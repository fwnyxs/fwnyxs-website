from datetime import date, datetime
import os
import platform
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import oracledb
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=None)

QUERY = """
SELECT B056_DOC_NUM, b056_name, B056_CTRY_DOC, B056_DATE_MOVEMENT,
       B056_TIME_MOVEMENT, SISTEM, MOVEMENT, B056_CREATE_DATE,
       b056_update_date, ROUND(
           (EXTRACT(DAY FROM time_int) * 86400) +
           (EXTRACT(HOUR FROM time_int) * 3600) +
           (EXTRACT(MINUTE FROM time_int) * 60) +
           EXTRACT(SECOND FROM time_int), 0
       ) AS BEZA_SAAT
FROM (
    SELECT TRIM(B056_DOC_NUM) AS B056_DOC_NUM,
           b056_name,
           B056_CTRY_DOC,
           TO_CHAR(B056_DATE_MOVEMENT, 'DD/MM/YYYY') AS B056_DATE_MOVEMENT,
           SUBSTR(LPAD(RTRIM(TO_CHAR(B056_TIME_MOVEMENT, 'HH24MISS')), 6, '0'), 1, 2) || ':' ||
           SUBSTR(LPAD(RTRIM(TO_CHAR(B056_TIME_MOVEMENT, 'HH24MISS')), 6, '0'), 3, 2) || ':' ||
           SUBSTR(LPAD(RTRIM(TO_CHAR(B056_TIME_MOVEMENT, 'HH24MISS')), 6, '0'), 5, 2) AS B056_TIME_MOVEMENT,
           CASE WHEN SUBSTR(B056_CREATE_ID, 1, 2) = 'NA' THEN 'NIISE' ELSE 'MYIMMS' END AS SISTEM,
           DECODE(B056_TYP_MOVEMENT, 1, 'MASUK', 2, 'KELUAR') AS MOVEMENT,
           B056_CREATE_DATE,
           b056_update_date,
           TO_TIMESTAMP(b056_update_date, 'DD-MON-RR HH.MI.SS.FF9 AM') -
           TO_TIMESTAMP(B056_CREATE_DATE, 'DD-MON-RR HH.MI.SS.FF9 AM') AS time_int
    FROM ibc.B056_MVMENT_FOR
    WHERE TRUNC(B056_DATE_MOVEMENT) = TO_DATE(:movement_date, 'YYYY-MM-DD')
      AND B056_BRANCH_CODE = :branch_code
    ORDER BY B056_DOC_NUM
) A
"""

DAILY_SUMMARY_QUERY = """
WITH movement_data AS (
    SELECT B056_DATE_MOVEMENT AS movement_date,
        NVL(TRIM(B056_CTZNSHP), 'UNKNOWN') AS citizenship,
        TRIM(B056_NUM_DEVICES) AS machine_no,
        B056_TYP_MOVEMENT AS movement_type,
        UPPER(TRIM(B056_FIRST_VISIT)) AS usage_code
    FROM IBC.B056_MVMENT_FOR
        WHERE B056_DATE_MOVEMENT >= TRUNC(SYSDATE)
            AND B056_DATE_MOVEMENT < TRUNC(SYSDATE) + 1
            AND B056_BRANCH_CODE = '1001121'
      AND UPPER(TRIM(B056_FIRST_VISIT)) IN ('M', 'D', 'P', 'Q', 'G', 'O', 'T', 'U')
    UNION ALL
    SELECT B078_DATE_MOVEMENT, NVL(TRIM(B078_CTZNSHP), 'UNKNOWN'),
        TRIM(B078_NUM_DEVICES), B078_TYP_MOVEMENT,
        UPPER(TRIM(B078_FIRST_VISIT))
    FROM IBC.B078_MVMENT_HISTFOR
        WHERE B078_DATE_MOVEMENT >= TRUNC(SYSDATE)
            AND B078_DATE_MOVEMENT < TRUNC(SYSDATE) + 1
            AND B078_NAME_BRANCH = '1001121'
      AND UPPER(TRIM(B078_FIRST_VISIT)) IN ('M', 'D', 'P', 'Q', 'G', 'O', 'T', 'U')
    UNION ALL
    SELECT B058_DATE_MOVEMENT, 'MALAYSIA', TRIM(B058_NUM_DEVICES),
        B058_TYP_MOVEMENT, UPPER(TRIM(B058_FP_STS_VERIFY))
    FROM IBC.B058_MVMNT_CIT
        WHERE B058_DATE_MOVEMENT >= TRUNC(SYSDATE)
            AND B058_DATE_MOVEMENT < TRUNC(SYSDATE) + 1
            AND B058_BRANCH_CODE = '1001121'
      AND UPPER(TRIM(B058_FP_STS_VERIFY)) IN ('M', 'D', 'P', 'Q', 'G', 'O', 'T', 'U')
    UNION ALL
    SELECT B077_DATE_MOVEMENT, 'MALAYSIA', TRIM(B077_NUM_DEVICES),
        B077_TYP_MOVEMENT, UPPER(TRIM(B077_FP_STS_VERIFY))
    FROM IBC.B077_MVMENT_HISTCIT
        WHERE B077_DATE_MOVEMENT >= TRUNC(SYSDATE)
            AND B077_DATE_MOVEMENT < TRUNC(SYSDATE) + 1
            AND B077_BRANCH_CODE = '1001121'
      AND UPPER(TRIM(B077_FP_STS_VERIFY)) IN ('M', 'D', 'P', 'Q', 'G', 'O', 'T', 'U')
), classified_data AS (
    SELECT TRUNC(movement_date) AS movement_date, citizenship,
        NVL(machine_no, 'UNKNOWN') AS machine_no, movement_type, usage_code,
        CASE WHEN machine_no IN ('301', '0301', '302', '0302')
          THEN 'NIISe' ELSE 'myIMMs' END AS system_name
    FROM movement_data
)
SELECT 'LTA SENAI' AS branch, TO_CHAR(movement_date, 'YYYYMMDD') AS hari,
    citizenship AS warganegara, machine_no AS machno, system_name AS sistem,
    SUM(CASE WHEN usage_code = 'M' AND movement_type = '1' THEN 1 ELSE 0 END) AS ebike_niise_masuk,
    SUM(CASE WHEN usage_code = 'M' AND movement_type = '2' THEN 1 ELSE 0 END) AS ebike_niise_keluar,
    SUM(CASE WHEN usage_code = 'D' AND movement_type = '1' THEN 1 ELSE 0 END) AS egate_qr_masuk,
    SUM(CASE WHEN usage_code = 'D' AND movement_type = '2' THEN 1 ELSE 0 END) AS egate_qr_keluar,
    SUM(CASE WHEN usage_code = 'P' AND movement_type = '1' THEN 1 ELSE 0 END) AS egate_passport_masuk,
    SUM(CASE WHEN usage_code = 'P' AND movement_type = '2' THEN 1 ELSE 0 END) AS egate_passport_keluar,
    SUM(CASE WHEN usage_code = 'Q' AND movement_type = '1' THEN 1 ELSE 0 END) AS individual_counter_masuk,
    SUM(CASE WHEN usage_code = 'Q' AND movement_type = '2' THEN 1 ELSE 0 END) AS individual_counter_keluar,
    SUM(CASE WHEN usage_code = 'G' AND movement_type = '1' THEN 1 ELSE 0 END) AS group_counter_masuk,
    SUM(CASE WHEN usage_code = 'G' AND movement_type = '2' THEN 1 ELSE 0 END) AS group_counter_keluar,
    SUM(CASE WHEN usage_code = 'O' AND movement_type = '1' THEN 1 ELSE 0 END) AS passport_counter_masuk,
    SUM(CASE WHEN usage_code = 'O' AND movement_type = '2' THEN 1 ELSE 0 END) AS passport_counter_keluar,
    SUM(CASE WHEN usage_code = 'T' AND movement_type = '1' THEN 1 ELSE 0 END) AS tris_ebike_masuk,
    SUM(CASE WHEN usage_code = 'T' AND movement_type = '2' THEN 1 ELSE 0 END) AS tris_ebike_keluar,
    SUM(CASE WHEN usage_code = 'U' AND movement_type = '1' THEN 1 ELSE 0 END) AS tris_egate_qr_masuk,
    SUM(CASE WHEN usage_code = 'U' AND movement_type = '2' THEN 1 ELSE 0 END) AS tris_egate_qr_keluar,
    SUM(CASE WHEN movement_type = '1' THEN 1 ELSE 0 END) AS jumlah_masuk,
    SUM(CASE WHEN movement_type = '2' THEN 1 ELSE 0 END) AS jumlah_keluar,
    COUNT(*) AS jumlah_keseluruhan
FROM classified_data
GROUP BY movement_date, citizenship, machine_no, system_name
ORDER BY movement_date, citizenship, machine_no, system_name
"""

TABLESPACE_QUERY = """
SELECT ROUND(SPACE_LIMIT / 1024 / 1024 / 1024, 2) AS LIMIT_GB,
       ROUND(SPACE_USED / 1024 / 1024 / 1024, 2) AS USED_GB,
       ROUND((SPACE_LIMIT - SPACE_USED) / 1024 / 1024 / 1024, 2) AS FREE_GB,
       ROUND((SPACE_USED / SPACE_LIMIT) * 100, 2) AS USED_PCT
FROM V$RECOVERY_FILE_DEST
"""

INSTANCE_QUERY = """
SELECT SYS_CONTEXT('USERENV', 'INSTANCE_NAME') AS INSTANCE_NAME,
       SYS_CONTEXT('USERENV', 'SERVER_HOST') AS SERVER_HOST
FROM dual
"""

DATABASES = {
    "DB01 / MIGPROD": "10.23.124.172:1521/migprod",
    "DB02 / DBPRACB 216": "10.29.249.216:1521/dbpracb",
    "DB03 / DBPRACB 218": "10.29.249.218:1521/dbpracb",
    "DB04 / DBPRACC": "10.29.249.220:1521/dbpracc",
    "DB05 / DBPRACD": "10.29.249.222:1521/dbpracd",
}

TRAINING_DATABASES = {
    "DB01 / DBSRACA": "172.16.9.91:1521/dbsraca",
    "DB02 / DBSRACB": "172.16.9.91:1521/dbsracb",
    "DB03 / DBRSACC": "172.16.9.91:1521/dbrsacc",
    "DB04 / DBSRACD": "172.16.9.91:1521/dbsracd",
}


def get_oracle_credentials():
    user = os.environ.get("ORACLE_USER", "system")
    password = os.environ.get("ORACLE_PASSWORD", "Oracle123")
    return user.strip().strip("'\"").strip(), password.strip().strip("'\"").strip()


def get_connection():
    user, password = get_oracle_credentials()
    return oracledb.connect(
        user=user,
        password=password,
        dsn=os.environ["ORACLE_CONNECT_STRING"],
    )


def query_database(database_name, dsn):
    connection = None
    cursor = None
    query_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    host_ip = dsn.split(":")[0] if ":" in dsn else dsn

    try:
        user, password = get_oracle_credentials()
        connection = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn,
        )
        cursor = connection.cursor()
        cursor.execute(TABLESPACE_QUERY)
        row = cursor.fetchone()
        columns = [column[0] for column in cursor.description]
        values = dict(zip(columns, row)) if row else {
            "LIMIT_GB": None,
            "USED_GB": None,
            "FREE_GB": None,
            "USED_PCT": None,
        }

        cursor.execute(INSTANCE_QUERY)
        instance_row = cursor.fetchone()
        instance_name = instance_row[0] if instance_row and instance_row[0] else "unknown"
        server_host = instance_row[1] if instance_row and len(instance_row) > 1 and instance_row[1] else host_ip

        error_message = ""
        if row is None:
            error_message = "No FRA configured"

        return {
            "database": database_name,
            "dsn": dsn,
            "instance": instance_name,
            "ip_address": server_host,
            "query_time": query_time,
            "status": "Connected",
            "error": error_message,
            **values,
        }
    except KeyError:
        return {
            "database": database_name,
            "dsn": dsn,
            "instance": "n/a",
            "ip_address": host_ip,
            "query_time": query_time,
            "status": "Missing credentials",
            "error": "Set ORACLE_USER and ORACLE_PASSWORD.",
        }
    except oracledb.Error as error:
        app.logger.warning("Tablespace query failed for %s: %s", database_name, error)
        return {
            "database": database_name,
            "dsn": dsn,
            "instance": "n/a",
            "ip_address": host_ip,
            "query_time": query_time,
            "status": "Connection failed",
            "error": str(error).splitlines()[0],
        }
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


@app.get("/")
def dashboard():
    return send_from_directory(BASE_DIR, "oracle-dashboard.html")


@app.get("/daily-summary")
def daily_summary_dashboard():
    return send_from_directory(BASE_DIR, "daily-summary.html")


@app.get("/system-status")
def system_status_dashboard():
    return send_from_directory(BASE_DIR, "system-status.html")


@app.get("/tablespace")
def tablespace_dashboard():
    return send_from_directory(BASE_DIR, "tablespace.html")


@app.get("/tablespace-training")
def tablespace_training_dashboard():
    return send_from_directory(BASE_DIR, "tablespace-training.html")


@app.get("/api/tablespace")
def tablespace():
    requested_database = request.args.get("database")
    selected = list(DATABASES.items())

    if requested_database and requested_database in DATABASES:
        selected = [(requested_database, DATABASES[requested_database])]
    elif requested_database:
        selected = []

    with ThreadPoolExecutor(max_workers=max(1, len(selected))) as executor:
        futures = [
            executor.submit(query_database, database_name, dsn)
            for database_name, dsn in selected
        ]
        rows = [future.result() for future in as_completed(futures)]

    if not requested_database:
        rows = [
            row for row in rows if row["database"] in DATABASES
        ]

    rows.sort(key=lambda row: row["database"])
    return jsonify(rows=rows)


@app.get("/api/tablespace-training")
def tablespace_training():
    requested_database = request.args.get("database")
    selected = list(TRAINING_DATABASES.items())

    if requested_database and requested_database in TRAINING_DATABASES:
        selected = [(requested_database, TRAINING_DATABASES[requested_database])]
    elif requested_database:
        selected = []

    with ThreadPoolExecutor(max_workers=max(1, len(selected))) as executor:
        futures = [
            executor.submit(query_database, database_name, dsn)
            for database_name, dsn in selected
        ]
        rows = [future.result() for future in as_completed(futures)]

    if not requested_database:
        rows = [
            row for row in rows if row["database"] in TRAINING_DATABASES
        ]

    rows.sort(key=lambda row: row["database"])
    return jsonify(rows=rows)


@app.get("/api/tablespace-training-a")
def tablespace_training_a():
    result = query_database("DB01 / DBSRACA", TRAINING_DATABASES["DB01 / DBSRACA"])
    return jsonify(rows=[result])


@app.get("/api/tablespace-training-b")
def tablespace_training_b():
    result = query_database("DB02 / DBSRACB", TRAINING_DATABASES["DB02 / DBSRACB"])
    return jsonify(rows=[result])


@app.get("/api/tablespace-training-c")
def tablespace_training_c():
    result = query_database("DB03 / DBRSACC", TRAINING_DATABASES["DB03 / DBRSACC"])
    return jsonify(rows=[result])


@app.get("/api/tablespace-training-d")
def tablespace_training_d():
    result = query_database("DB04 / DBSRACD", TRAINING_DATABASES["DB04 / DBSRACD"])
    return jsonify(rows=[result])


def parse_ggsci_lines(output_text):
    lines = []
    for raw_line in (output_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("GGSCI") or line.startswith("Oracle GoldenGate"):
            continue
        if line.lower().startswith("program") and "status" in line.lower():
            continue
        if line.lower().startswith("info all"):
            continue
        if "1>" in line and "info all" in line.lower():
            continue

        pieces = [part for part in re.split(r"\s{2,}", line) if part.strip()]
        if len(pieces) >= 2:
            row = {
                "program": pieces[0],
                "status": pieces[1],
                "group": pieces[2] if len(pieces) > 2 else "",
                "lag": pieces[3] if len(pieces) > 3 else "",
                "time": pieces[4] if len(pieces) > 4 else "",
            }
            lines.append(row)
    return lines


@app.get("/api/ggsci-info")
def ggsci_info():
    host = os.environ.get("GGSCI_HOST")
    user = os.environ.get("GGSCI_USER", "oracle")

    if not host:
        return jsonify({
            "error": "GGSCI_HOST is not configured. Set GGSCI_HOST=<server-host>",
            "rows": [],
            "output": "",
        }), 400

    ssh_target = f"{user}@{host}"
    remote_command = "bash -lc 'cd \"${OGG_HOME}\" && printf \"info all\\nexit\\n\" | ./ggsci'"

    try:
        result = subprocess.run(
            ["ssh", ssh_target, remote_command],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return jsonify({
            "error": str(exc),
            "rows": [],
            "output": "",
        }), 500

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    rows = parse_ggsci_lines(stdout)
    payload = {
        "output": stdout,
        "error": stderr,
        "rows": rows,
    }

    if result.returncode != 0:
        return jsonify(payload), 500

    return jsonify(payload)


@app.route("/ggsci-monitor")
def ggsci_monitor_page():
    return send_from_directory(BASE_DIR, "ggsci-monitor.html")


@app.get("/api/system/disk")
def disk_status():
    command = ["wsl.exe", "--", "df", "-h"]
    ip_command = ["wsl.exe", "--", "hostname", "-I"]
    if platform.system() != "Windows":
        command = ["df", "-h"]
        ip_command = ["hostname", "-I"]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return jsonify(error="Disk usage command could not be run."), 500

    if result.returncode != 0:
        return jsonify(error=result.stderr.strip() or "Disk usage command failed."), 500

    ip_result = subprocess.run(
        ip_command,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    ip_address = next(
        (value for value in ip_result.stdout.split() if "." in value),
        "Unavailable",
    )
    return jsonify(
        hostname=socket.gethostname(),
        ip_address=ip_address,
        output=result.stdout,
    )


@app.get("/api/movements")
def movements():
    movement_date = request.args.get("movementDate", "")
    branch_code = request.args.get("branchCode", "")

    try:
        date.fromisoformat(movement_date)
    except ValueError:
        return jsonify(error="Enter a valid movement date."), 400

    if not branch_code.isdigit():
        return jsonify(error="Enter a numeric branch code."), 400

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            QUERY,
            movement_date=movement_date,
            branch_code=branch_code,
        )
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(rows=rows)
    except KeyError as error:
        app.logger.error("Missing environment variable: %s", error)
        return jsonify(error="Oracle environment variables are not configured."), 500
    except oracledb.Error:
        app.logger.exception("Oracle query failed")
        return jsonify(error="Oracle query failed. Check database access and configuration."), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


@app.get("/api/daily-summary")
def daily_summary():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(DAILY_SUMMARY_QUERY)
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(rows=rows)
    except KeyError as error:
        app.logger.error("Missing environment variable: %s", error)
        return jsonify(error="Oracle environment variables are not configured."), 500
    except oracledb.Error:
        app.logger.exception("Oracle summary query failed")
        return jsonify(error="Oracle summary query failed. Check database access and configuration."), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)

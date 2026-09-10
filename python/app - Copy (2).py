from datetime import date
import os
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
    WHERE B056_DATE_MOVEMENT >= TO_DATE(:movement_date, 'YYYY-MM-DD')
      AND B056_DATE_MOVEMENT < TO_DATE(:movement_date, 'YYYY-MM-DD') + 1
      AND B056_BRANCH_CODE = :branch_code
      AND UPPER(TRIM(B056_FIRST_VISIT)) IN ('M', 'D', 'P', 'Q', 'G', 'O', 'T', 'U')
    UNION ALL
    SELECT B078_DATE_MOVEMENT, NVL(TRIM(B078_CTZNSHP), 'UNKNOWN'),
        TRIM(B078_NUM_DEVICES), B078_TYP_MOVEMENT,
        UPPER(TRIM(B078_FIRST_VISIT))
    FROM IBC.B078_MVMENT_HISTFOR
    WHERE B078_DATE_MOVEMENT >= TO_DATE(:movement_date, 'YYYY-MM-DD')
      AND B078_DATE_MOVEMENT < TO_DATE(:movement_date, 'YYYY-MM-DD') + 1
      AND B078_NAME_BRANCH = :branch_code
      AND UPPER(TRIM(B078_FIRST_VISIT)) IN ('M', 'D', 'P', 'Q', 'G', 'O', 'T', 'U')
    UNION ALL
    SELECT B058_DATE_MOVEMENT, 'MALAYSIA', TRIM(B058_NUM_DEVICES),
        B058_TYP_MOVEMENT, UPPER(TRIM(B058_FP_STS_VERIFY))
    FROM IBC.B058_MVMNT_CIT
    WHERE B058_DATE_MOVEMENT >= TO_DATE(:movement_date, 'YYYY-MM-DD')
      AND B058_DATE_MOVEMENT < TO_DATE(:movement_date, 'YYYY-MM-DD') + 1
      AND B058_BRANCH_CODE = :branch_code
      AND UPPER(TRIM(B058_FP_STS_VERIFY)) IN ('M', 'D', 'P', 'Q', 'G', 'O', 'T', 'U')
    UNION ALL
    SELECT B077_DATE_MOVEMENT, 'MALAYSIA', TRIM(B077_NUM_DEVICES),
        B077_TYP_MOVEMENT, UPPER(TRIM(B077_FP_STS_VERIFY))
    FROM IBC.B077_MVMENT_HISTCIT
    WHERE B077_DATE_MOVEMENT >= TO_DATE(:movement_date, 'YYYY-MM-DD')
      AND B077_DATE_MOVEMENT < TO_DATE(:movement_date, 'YYYY-MM-DD') + 1
      AND B077_BRANCH_CODE = :branch_code
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


def get_connection():
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_CONNECT_STRING"],
    )


@app.get("/")
def dashboard():
    return send_from_directory(BASE_DIR, "oracle-dashboard.html")


@app.get("/daily-summary")
def daily_summary_dashboard():
    return send_from_directory(BASE_DIR, "daily-summary.html")


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
            DAILY_SUMMARY_QUERY,
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
        app.logger.exception("Oracle summary query failed")
        return jsonify(error="Oracle summary query failed. Check database access and configuration."), 500
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)

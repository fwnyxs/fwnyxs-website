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


def get_connection():
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_CONNECT_STRING"],
    )


@app.get("/")
def dashboard():
    return send_from_directory(BASE_DIR, "oracle-dashboard.html")


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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)

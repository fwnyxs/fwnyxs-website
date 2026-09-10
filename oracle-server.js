const express = require('express');
const oracledb = require('oracledb');
const path = require('path');

const app = express();
const port = Number(process.env.PORT || 3000);
const poolConfig = {
  user: process.env.ORACLE_USER,
  password: process.env.ORACLE_PASSWORD,
  connectString: process.env.ORACLE_CONNECT_STRING,
  poolMin: 1,
  poolMax: 5,
  poolIncrement: 1
};
const query = `
SELECT B056_DOC_NUM, b056_name, B056_CTRY_DOC, B056_DATE_MOVEMENT, B056_TIME_MOVEMENT, SISTEM, MOVEMENT, B056_CREATE_DATE, b056_update_date,
    ROUND(
        (EXTRACT(DAY FROM time_int) * 86400) +
        (EXTRACT(HOUR FROM time_int) * 3600) +
        (EXTRACT(MINUTE FROM time_int) * 60) +
        EXTRACT(SECOND FROM time_int), 0
    ) AS BEZA_SAAT
FROM (
    SELECT trim(B056_DOC_NUM) AS B056_DOC_NUM,
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
           TO_TIMESTAMP(b056_update_date, 'DD-MON-RR HH.MI.SS.FF9 AM') - TO_TIMESTAMP(B056_CREATE_DATE, 'DD-MON-RR HH.MI.SS.FF9 AM') AS time_int
    FROM ibc.B056_MVMENT_FOR
    WHERE TRUNC(B056_DATE_MOVEMENT) = TO_DATE(:movementDate, 'YYYY-MM-DD')
      AND B056_BRANCH_CODE = :branchCode
    ORDER BY B056_DOC_NUM
) A`;

app.use(express.static(__dirname));
app.get('/api/movements', async (request, response) => {
  const { movementDate, branchCode } = request.query;
  if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(movementDate || '') || !/^\\d+$/.test(branchCode || '')) {
    return response.status(400).json({ error: 'Enter a valid date and numeric branch code.' });
  }
  let connection;
  try {
    connection = await oracledb.getConnection();
    const result = await connection.execute(query, { movementDate, branchCode }, { outFormat: oracledb.OUT_FORMAT_OBJECT });
    response.json({ rows: result.rows });
  } catch (error) {
    console.error(error);
    response.status(500).json({ error: 'Oracle query failed. Check the server configuration and database access.' });
  } finally {
    if (connection) await connection.close();
  }
});

async function start() {
  await oracledb.createPool(poolConfig);
  app.listen(port, () => console.log(`Movement monitor: http://localhost:${port}/oracle-dashboard.html`));
}
start().catch(error => { console.error(error); process.exit(1); });

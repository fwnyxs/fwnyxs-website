# WSL Ubuntu setup

This project can run from Ubuntu under WSL without depending on the Windows environment.

## 1) Open WSL Ubuntu

From the Ubuntu terminal:

```bash
cd /mnt/c/temp/fwnyxs
bash ./setup-wsl.sh
```

This creates a local virtual environment and installs the Python packages from [python/requirements.txt](python/requirements.txt).

## 2) Start the app

```bash
cd /mnt/c/temp/fwnyxs
bash ./run-wsl.sh
```

The app will start on:

```text
http://127.0.0.1:5000
```

## 3) Optional custom environment

Create a local file named `.env` based on `wsl.env.example`:

```bash
cp wsl.env.example .env
```

Then edit `.env` and set your Oracle credentials and port. The default value is:

```bash
export ORACLE_USER="system"
export ORACLE_PASSWORD="Oracle123"
```

## 4) Notes

- This app already reads Oracle credentials from `ORACLE_USER` and `ORACLE_PASSWORD`.
- The service name and DSN values are configured in [python/app.py](python/app.py).
- If the Oracle listener or service names change, update the database definitions in [python/app.py](python/app.py).

## 5) Troubleshooting

If the app cannot connect to Oracle:

```bash
echo "$ORACLE_USER"
echo "$ORACLE_PASSWORD"
```

Check that the same values are present in your active shell before starting the app.

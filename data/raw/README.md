# Raw data (not committed)

Place the original, **unmodified** Kaggle CSV files in this folder. No script in this repository edits files here; all cleaning writes to `data/processed/`.

## Source

**Financial Data of 4400 Public Companies** by `qks1lver` on Kaggle
https://www.kaggle.com/datasets/qks1lver/financial-data-of-4400-public-companies

The dataset belongs to its original author and is subject to the licence terms on Kaggle. It is therefore excluded from version control (see `.gitignore`); anyone cloning this repository must download it themselves.

## Expected files

```text
balanceSheetHistory_annually.csv
balanceSheetHistory_quarterly.csv
cashflowStatement_annually.csv
cashflowStatement_quarterly.csv
incomeStatementHistory_annually.csv
incomeStatementHistory_quarterly.csv
```

## How to obtain

Download `archive.zip` from the dataset page and unzip the six CSVs into this folder, or with the Kaggle CLI:

```bash
kaggle datasets download -d qks1lver/financial-data-of-4400-public-companies -p data/raw --unzip
```

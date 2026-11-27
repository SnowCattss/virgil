# Changelog

## 0.1.1 - Selva oscura

- FASTQ links are looked up once per SRA study instead of once per run
  (GSE172335: 6 requests instead of 285), with run by run lookups only if a
  study request fails.
- Red review cells now show in Excel (they only showed in OnlyOffice prior).
- Downloads that time out partway through are retried.

## 0.1.0 – Selva oscura

First working version: `virgil fetch`, `virgil build`, the Studies overview,
Runs overview and Raw sheets, `--redo` and `-v`.
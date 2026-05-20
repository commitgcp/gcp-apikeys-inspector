# Generate a Commit GCP API Keys Report

This tutorial opens the repo in Cloud Shell and hands the workflow to Gemini
CLI.

## Trust And Authenticate

When Cloud Shell asks whether to trust this repository, approve it. In a trusted
repo, Cloud Shell is already authenticated as the signed-in user and the report
command can use that active gcloud session.

Before starting Gemini, verify that gcloud has an active account:

```bash
gcloud auth list --filter="status:ACTIVE" --format="value(account)"
```

If this prints your user email, continue to the next step. If it prints nothing,
authenticate first:

```bash
gcloud auth login --update-adc
```

## Start Gemini

In the Cloud Shell terminal, run:

```bash
gemini
```

## Run the Report Command

Inside Gemini CLI, run:

```text
/gcp-api-keys-discover
```

The command first lists visible organizations and quota-project candidates from
gcloud, Cloud Shell environment variables, visible organizations, and project
ancestors. Gemini asks which organization and quota project to use, then runs the
scanner with those explicit values. It uses the already-authenticated active
gcloud account and does not run `gcloud auth application-default login`.

The generated files are always overwritten at:

- `reports/index.html`
- `reports/report.json`

If the command is not visible, run:

```text
/commands reload
/commands list
```

Then run `/gcp-api-keys-discover` again.

## Download Or Preview

Gemini starts a local web server rooted at `reports/`, so Cloud Shell Web Preview
opens the HTML report directly instead of showing the repository directory.

You are still inside Gemini CLI after report generation. Exit Gemini first:

```text
/quit
```

Then download the files from the Cloud Shell terminal:

```bash
cloudshell download reports/index.html reports/report.json
```

Inspect the HTML report in Cloud Shell with the Web Preview menu in the
top-right toolbar. Choose `Preview on port 8080` when Gemini used port `8080`;
otherwise choose `Change port` and enter the port Gemini printed.

![Cloud Shell Web Preview menu](cloudshell/assets/web-preview.png)


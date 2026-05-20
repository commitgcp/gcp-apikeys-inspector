# Generate a Commit GCP API Keys Report

This tutorial opens the repo in Cloud Shell and hands the workflow to Gemini
CLI.

## Start Gemini

In the Cloud Shell terminal, run:

```bash
gemini
```

If Gemini asks whether to trust this workspace, approve it. In a trusted repo,
Cloud Shell is already authenticated as the signed-in user and the report command
can use that active gcloud session. If the workspace is not trusted, Gemini may
not be able to use the existing Cloud Shell session and the user may need to run
a separate `gcloud auth login` flow.

## Run the Report Command

Inside Gemini CLI, run:

```text
/gcp-api-keys-discover
```

The command runs the repository's deterministic Cloud Shell script. The script
discovers the organization ID and quota project from gcloud, Cloud Shell
environment variables, visible organizations, and project ancestors. It uses the
already-authenticated active gcloud account and does not run `gcloud auth
application-default login`.

If the command is not visible, run:

```text
/commands reload
/commands list
```

Then run `/gcp-api-keys-discover` again.

## Download Or Preview

Gemini prints the generated HTML and JSON paths under `reports/`.

Download the files to your local machine:

```bash
cloudshell download reports/<report>.html reports/<report>.json
```

Or preview the HTML report in Cloud Shell. If Gemini starts a Python web server,
use the Web Preview menu in the top-right toolbar. Choose `Preview on port 8080`
when Gemini used port `8080`; otherwise choose `Change port` and enter the port
Gemini printed.

<!-- TODO: Add Web Preview screenshot before committing.
Suggested path: cloudshell/assets/web-preview-8080.png
Suggested Markdown:
![Cloud Shell Web Preview menu](assets/web-preview-8080.png)
-->

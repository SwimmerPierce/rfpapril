# Human Setup Required: External Integrations

This document tracks manual setup steps that require human intervention (e.g., creating API credentials, authenticating OAuth apps). AI agents will update this file to request specific information or actions from the user.

## Instructions for the AI Agent
When a task requires human intervention:
1.  **Append** a new section under "Active Requests" describing exactly what is needed.
2.  Provide **step-by-step** instructions for the human to follow.
3.  Specify the **exact variable names** the human should add to the `.env` file.
4.  Do **not** ask for the keys in chat; instruct the human to place them directly in the `.env` file to maintain security.

---

## 🟢 Active Requests

### 1. Zoho CRM OAuth Configuration (Phase 3)
To enable the Zoho CRM synchronization, we need a Client ID, Client Secret, and a persistent Refresh Token.

**Steps for the Human:**
1.  Go to the [Zoho API Console](https://api-console.zoho.com/).
2.  Click **Add Client** and select **Self Client**.
3.  Under the **Generate Code** tab, enter the following scopes:
    - `ZohoCRM.modules.ALL`
    - `ZohoCRM.settings.ALL`
4.  Select a **Time Duration** (e.g., 10 minutes) and click **Generate**.
5.  Copy the **Grant Token** immediately.
6.  Use the Grant Token to generate the **Refresh Token** (you can use a `curl` command or Postman).
    - *Note: Access tokens expire, but the Refresh Token is permanent until revoked.*
7.  Add the following to your `.env` file:
    ```env
    ZOHO_CLIENT_ID=your_id_here
    ZOHO_CLIENT_SECRET=your_secret_here
    ZOHO_REFRESH_TOKEN=your_refresh_token_here
    ZOHO_BASE_URL=https://www.zohoapis.com  # Change if using .eu, .ca, etc.
    ```

### 2. Email / SMTP Configuration (Phase 4)
To enable daily morning reports, we need SMTP credentials.

**Steps for the Human:**
1.  Identify the SMTP server for your email provider (e.g., `smtp.office365.com` for Outlook).
2.  Create an App Password if your account uses Multi-Factor Authentication (MFA).
3.  Add the following to your `.env` file:
    ```env
    SMTP_SERVER=smtp.example.com
    SMTP_PORT=587
    SMTP_USER=your_email@example.com
    SMTP_PASSWORD=your_app_password
    ADMIN_EMAIL=admin@example.com
    ```

---

## 📂 Variable Placement
All sensitive variables (API keys, secrets, passwords) **MUST** be placed in the `.env` file located in the project root.

**Template:**
Refer to `.env.example` for the current required structure.

---

## ✅ Confirmation of Completion
*Human: Please check the boxes below once you have completed the setup.*

- [ ] **Zoho CRM:** Credentials added to `.env` and verified.
- [ ] **Email/SMTP:** Credentials added to `.env` and verified.
- [ ] **Database:** `DATABASE_URL` is configured and accessible.

---
*Last Updated: 2026-04-13*

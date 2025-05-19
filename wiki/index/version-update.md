# Updating OpenWebUI Image

This section outlines the procedure to update the OpenWebUI image by pulling the latest changes from the official OpenWebUI GitHub repository, merging them into your local development branch, ensuring that custom modifications are preserved, building and testing the image locally, committing the changes to your Azure DevOps repository, and preparing for deployment via Azure DevOps pipelines.

## Step 1: Add Remote Repository for Official OpenWebUI

1. **Navigate to Your Local Repository**:
   - Open a terminal or PowerShell in your local OpenWebUI project directory:
     ```
     cd C:\Projects\OpenWebUI
     ```

2. **Add the Official OpenWebUI Repository as a Remote**:
   - Add the official OpenWebUI GitHub repository as a remote named `upstream`:
     ```
     git remote add upstream https://github.com/open-webui/open-webui.git
     ```
   - Verify the remote was added:
     ```
     git remote -v
     ```
     You should see `upstream` listed alongside your Azure DevOps repository (`origin`).

## Step 2: Pull the Latest Changes from the Official Repository

1. **Fetch the Latest Changes**:
   - Fetch the latest changes from the `main` branch of the `upstream` repository:
     ```
     git fetch upstream
     ```

2. **Ensure You’re on Your Development Branch**:
   - Check out your local development branch (e.g., `dev`):
     ```
     git checkout dev
     ```
   - If the `dev` branch doesn’t exist, create it from your current branch:
     ```
     git checkout -b dev
     ```

3. **Merge the Upstream Changes**:
   - Merge the `main` branch from `upstream` into your `dev` branch:
     ```
     git merge upstream/main
     ```
   - If there are no conflicts, the merge will complete automatically. If conflicts arise, resolve them manually using your preferred Git tool (e.g., VS Code, `git mergetool`).
   - **Note on `git add`**: The `git merge` command does not automatically stage changes. If there were merge conflicts that you resolved, you must stage the resolved files using:
     ```
     git add <resolved-file>
     ```
     After resolving conflicts, complete the merge by committing:
     ```
     git commit
     ```
     If there were no conflicts, Git will automatically commit the merge, and no additional `git add` or `git commit` is needed at this stage.

## Step 3: Compare and Verify Custom Modifications

After merging, ensure that none of your custom modifications are affected. Refer to the following wiki pages for the specific files and modifications to check:

- **[Tikehau Capital Lagoon Branding](/index/tikehau-branding.md)**: Verify that all branding-related static resources and configuration changes are preserved.
- **[Azure AI Foundry Support](/index/azure-ai-foundry.md)**: Confirm that the Azure AI API version configurations and backend modifications for API calls are intact.
- **[Teams Custom Integration](/index/teams-integration.md)**: Ensure that all Teams-related changes, including SDK integration, authentication routes, and security headers, are unaffected.

### Special Attention: Authentication Functions in `backend/open_webui/main.py`

Pay close attention to the authentication logic in `backend/open_webui/main.py`, as detailed in the [Teams Custom Integration](/index/teams-integration.md) page:
- Verify the OAuth authentication flow (native flow) remains intact, including token exchange and user session creation.
- Ensure the Teams SSO section is unchanged.
- Confirm the `TeamsRedirectMiddleware` for redirecting root path requests in Teams contexts is preserved.

**Action**:
- If any custom modifications have been overwritten by the upstream merge, restore them using your Git history (e.g., `git checkout HEAD^ -- <file>` to revert specific files). Use `git diff` to identify changes if needed.

## Step 4: Build and Test the Image Locally

Before committing changes, build and test the updated image locally to ensure compatibility with your customizations.

1. **Determine the New Version Tag**:
   - The current latest version of OpenWebUI is `v0.5.5`. For this update, use `v0.5.6` as the new version tag.

2. **Build the Docker Image**:
   - In your project directory, build the Docker image with the new version tag and also tag it as `latest`:
     ```
     docker build -t lagoon-open-webui:v0.5.5 -t lagoon-open-webui:latest .
     ```

3. **Test with Local Docker Compose**:
   - Update the `docker-compose.yaml` file to use the newly built image:
     ```yaml
     services:
       open-webui:
         image: lagoon-open-webui:v0.5.6
         # ... other configurations ...
     ```
   - Start the services using Docker Compose (Ngrok is already configured in your `docker-compose.yaml`):
     ```
     docker compose up -d
     ```
   - Access OpenWebUI using the Ngrok URL provided by your Docker Compose setup (e.g., check the Ngrok service logs for the public URL).

4. **Verify Functionality**:
   - **SSO Authentication**: Log in using Entra ID SSO to ensure the OAuth flow works correctly.
   - **Teams Integration**: Test the Teams authentication flow by accessing the `/teams` route or embedding OpenWebUI in a Teams tab (refer to [Teams Custom Integration](/index/teams-integration.md)).
   - **Branding**: Verify that all Tikehau Capital Lagoon branding assets are displayed correctly (refer to [Tikehau Capital Lagoon Branding](/index/tikehau-branding.md)).
   - **Azure AI Foundry**: Test API calls to Azure AI Foundry to ensure the custom configurations are functioning (refer to [Azure AI Foundry Support](/index/azure-ai-foundry.md)).
   - **General Functionality**: Test core features like chat, document processing, and model interactions to ensure no regressions.

5. **Troubleshoot Issues**:
   - If any issues arise, check the Docker logs:
     ```
     docker compose logs
     ```
   - Address any errors by reverting problematic changes or applying necessary patches.

## Step 5: Update `docker-compose.yaml` for Production

1. **Update the Image Tag**:
   - Ensure the `docker-compose.yaml` file reflects the new image tag for production deployment:
     ```yaml
     services:
       open-webui:
         image: lagoon-open-webui:v0.5.6
         # ... other configurations ...
     ```

2. **Test the Production Configuration**:
   - Run the updated `docker-compose.yaml` locally to confirm it works as expected:
     ```
     docker compose up -d
     ```
   - Perform a final round of testing to ensure the application behaves correctly.

## Step 6: Commit and Push Changes to Azure DevOps

1. **Stage and Commit Changes**:
   - Stage all modified files, including the updated `docker-compose.yaml`:
     ```
     git add .
     ```
   - Commit the changes with a descriptive message:
     ```
     git commit -m "Update OpenWebUI to v0.5.6 with upstream changes"
     ```

2. **Push to Azure DevOps**:
   - Push the changes to your Azure DevOps repository:
     ```
     git push origin dev
     ```
   - Ensure the `dev` branch is updated in your Azure DevOps project.

## Step 7: Remove the Upstream Remote

1. **Remove the Upstream Remote**:
   - Remove the `upstream` remote to avoid accidental pulls in the future:
     ```
     git remote remove upstream
     ```
   - Verify the remote is removed:
     ```
     git remote -v
     ```

## Step 8: Deploy to Production via Azure DevOps Pipelines

- **Note on Docker Push**: You do not need to manually push the Docker image to Azure Container Registry (ACR). Azure DevOps pipelines are configured to handle the build and push of the `lagoon-open-webui:v0.5.6` and `lagoon-open-webui:latest` images to ACR as part of the deployment process.
- After pushing the changes to Azure DevOps, trigger your deployment pipeline to build and deploy the updated image to your production environment.
- Monitor the deployment for any issues and roll back if necessary.

---

This procedure ensures that the OpenWebUI image is updated safely while preserving all custom modifications, with references to the relevant wiki pages for detailed modification lists.
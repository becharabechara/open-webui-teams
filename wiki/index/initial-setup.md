# Initial OpenWebUI Setup

This section outlines the steps and parameters required to set up the OpenWebUI solution properly. The setup process includes configuring admin settings, managing user access, setting up custom functions, and ensuring model visibility aligns with organizational requirements.

## Step 1: Admin User Setup

1. **First Admin Account**:
   - The first user to connect to the OpenWebUI solution will automatically be granted admin privileges.
   - This admin user is responsible for approving all subsequent user creations until the environment is fully configured.
   - Ensure the admin user logs in using the OAuth flow (via Microsoft Entra ID, as configured in the environment variables) to establish the initial admin account.

## Step 2: Configure Admin Settings

Navigate to the **Admin Panel** in OpenWebUI to configure the settings as follows:

### General Tab

#### Authentication
- **Default User Role**: Set to `user`. This ensures that new users are assigned the `user` role by default, restricting their access until the admin assigns higher privileges.
- **Enable New Sign Ups**: Set to `Active`. This allows new users to sign up via OAuth (Microsoft Entra ID in this case).
- **Show Admin Details in Account Pending Overlay**: Set to `Active`. This displays admin contact details to users awaiting approval, facilitating communication.
- **Enable API Key**: Set to `Active`. This enables users to generate API keys for programmatic access to OpenWebUI.
- **API Key Endpoint Restrictions**: Set to `Disabled`. This allows API keys to access all endpoints without restrictions.

#### Features
- **Enable Community Sharing**: Set to `Active`. This allows users to share content with the community.
- **Enable Message Rating**: Set to `Active`. This enables users to rate messages, providing feedback on responses.
- **Channels (Beta)**: Set to `Disabled`. Channels are not used in this setup.
- **User Webhooks**: Set to `Active`. This enables users to configure webhooks for custom integrations.
- **WebUI Url**: Set to `<matches the public dns url>`. This should match the public DNS URL of your OpenWebUI instance (e.g., the value of `WEBUI_URL` from the environment variables, such as `https://<public-domain>`).

### Connection Tab

- **Disable All Connections**: Ensure all external connections (e.g., third-party integrations) are disabled to prevent unauthorized access during setup.

### Evaluation Tab

- **Disable Arena Models**: Disable any Arena Models to prevent evaluation features from being active during the initial setup.

### Web Search Tab

- **Activate Web Search**: Enable web search functionality.
- **Search Engine**: Select `bing` as the search engine.
- **Bing Search V7 Subscription Key**: Enter your Bing Search V7 subscription key (obtained from Azure).
- **Search Result Count**: Set to `2`. This limits the number of search results returned to 2.
- **Concurrent Requests**: Set to `2`. This allows up to 2 concurrent web search requests.
- **Bypass Embedding and Retrieval**: Set to `On`. This skips embedding and retrieval steps for web search results, directly using raw search data.
- **Bypass SSL Verification for Websites**: Set to `On`. This disables SSL verification for web search requests, useful for testing but should be re-evaluated for production.

### Code Execution Tab

- **Enable Code Execution and Interpreter**: Ensure both are activated.
- **Interpreter**: Select `pyodide`. This uses Pyodide for in-browser Python code execution, ensuring compatibility with the OpenWebUI environment.

### Interface Tab

- **Local Models and External Models Dropdown**: Ensure the dropdown lists show `Current Model` as the selected option for both Local and External Models.
- **Title Generation**: Set to `Active`. This enables automatic title generation for conversations.
  - **Title Generation Prompt**: Copy the prompt from the DevOps repository at `/Custom_Functions/Title_Custom_Prompt.txt` and paste it into the Title Generation Prompt field.
- **Tags Generation**: Set to `Active`. This enables automatic tag generation for content.
- **Retrieval Query Generation**: Set to `Active`. This enables generation of queries for retrieval.
- **Autocomplete Generation**: Set to `Active`. This enables autocomplete suggestions.
- **Web Search Query Generation**: Set to `Active`. This enables generation of web search queries.
  - **Web Search Query Generation Prompt**: Replace the default prompt with the one from the DevOps repository at `/Custom_Functions/Search_Custom_Prompt.txt`.

### Documents Tab

- **Content Extraction Engine**: Select `Tika` from the dropdown.
  - Verify that the URL matches the environment variable `TIKA_SERVER_ENDPOINT`, which should be `http://tika:9998`.
- **Bypass Embedding and Retrieval**: Ensure this is `Not Active`. This ensures embeddings are generated for document content.
- **Text Splitter**: Select `Tiktoken`. This uses the Tiktoken library for text splitting.
- **Chunk Size**: Set to `1000`. This defines the size of text chunks for processing.
- **Chunk Overlap**: Set to `200`. This specifies the overlap between chunks for better context retention.
- **Embedding Model Engine**: Select `Default (SentenceTransformers)`.
  - Click `Download` on the default model `sentence-transformers/all-MiniLM-L6-v2` to ensure it’s available for embedding.
- **Retrieval**:
  - **Hybrid Search**: Set to `Active`. This enables hybrid search combining keyword and vector search.
  - **Top K**: Set to `10`. This returns the top 10 results from retrieval.
  - **Top K Reranker**: Set to `10`. This reranks the top 10 results for better relevance.
  - **Minimum Score**: Set to `0`. This includes all results regardless of score.
- **RAG Template**: Replace the default RAG template with the one from the DevOps repository at `/Custom_Functions/RAG_Custom_Prompt.txt`.
- **Files Max Upload Size and Count**: Set to `5`. This limits the maximum number of files that can be uploaded at once to 5.

### Models Tab

- After deploying the custom functions for Azure AI, Lagoon, and Lagoon DDQ (see below), a list of models should be available.
- Configure visibility for each model:
  - **Azure AI Models**: Set visibility to `Public` or `Private` based on your requirements.
  - **Lagoon Models**: Set visibility to `Public` or `Private` based on your requirements.
  - **Lagoon DDQ Models**: Set visibility to `Private` and ensure access is restricted to the `Lagoon DDQ` group (configured in the Users tab).

## Step 3: Configure User Groups

Navigate to the **Users Tab** in the Admin Panel:

1. **Groups Tab**:
   - Create a new group named `Lagoon DDQ`.
   - Add the desired users to this group.
2. **Model Visibility**:
   - Go back to the **Models Tab**.
   - For the `Lagoon DDQ` models, ensure the visibility is set to `Private` and select the `Lagoon DDQ` group in the visibility settings to restrict access.

## Step 4: Create Custom Functions

Navigate to the **Functions** section in the Admin Panel to create and configure the following custom functions. Ensure the names match exactly as specified, as they are referenced by their IDs elsewhere.

### Azure AI Foundry Function

- **Name**: `Azure AI` (ID: `azure_ai`)
- **Description**: `Azure AI: access to most models on Azure AI`
- **Content**: Copy the content from the DevOps repository at `/Custom_Functions/Azure_ai.py`.
- **Valves Configuration**:
  - **Azure AI API Key**: `<key from your Azure AI Foundry>`. Replace with the API key obtained from your Azure AI Foundry instance.
  - **Azure AI Endpoint**: `https://<azure ai service endpoints not model endpoint>/models/chat/completions?api-version=2024-05-01-preview`. Replace with your Azure AI service endpoint (e.g., `https://ais-fc-tko-lagon-dev-02.services.ai.azure.com/`).
  - **Azure AI Model**: Set to `Default Value`.
  - **Azure AI Model In Body**: Set to `Enabled`.
  - **Use Predefined Azure AI Models**: Set to `Enabled`.

### Lagoon Function

- **Name**: `Lagoon` (ID: `lagoon`)
- **Description**: `Lagoon DDQ`
- **Content**: Copy the content from the DevOps repository at `/Custom_Functions/Lagoon.py`.
- **Valves Configuration**: No valves to configure.

### Lagoon DDQ Function

- **Name**: `Lagoon DDQ` (ID: `lagoon_ddq`)
- **Description**: `Lagoon DDQ`
- **Content**: Copy the content from the DevOps repository at `/Custom_Functions/Lagoon_ddq.py`.
- **Valves Configuration**: No valves to configure.

## Step 5: Activate Functions and Configure Model Visibility

1. **Activate Functions**:
   - After creating the functions, activate them in the Functions section.
2. **Revisit Models Tab**:
   - Go back to **Admin Panel Settings > Models**.
   - Configure the visibility of the models associated with the newly created functions (Azure AI, Lagoon, Lagoon DDQ) as specified in the Models Tab section above.

---

This setup ensures that OpenWebUI is configured with the necessary settings, user groups, and custom functions to support your organization's requirements, including Azure AI integration, Lagoon branding, and restricted access to specific models.
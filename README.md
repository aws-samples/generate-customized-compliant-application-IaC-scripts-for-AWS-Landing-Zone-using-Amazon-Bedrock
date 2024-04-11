### README for Account Customization Lambda Function and Knowledge Base

#### Custom code generation Lambda Function
- **Description**: Generates and commits Terraform configurations for custom AWS services to a GitHub repository.
- **Environment Variables**:
  - `GITHUB_TOKEN`: Token for GitHub API authentication.
- **Dependencies**: Python 3.x, `boto3`, `requests`, `logging`, `base64` libraries.
- **Logical Flow**:
  1. Receives an event with detailed descripton of AWS application architecture.
  2. Identifies AWS service from description
  3. Retrieves Terraform module definitions for AWS services from the KB.
  4. Invokes the Bedrock model twice: first, to generate Terraform configurations following organizational coding guidelines and including Terraform module details from the Knowledge Base; second, to create a detailed README
  5. Applies Retrieval Augmented Generation (RAG) to enrich the input prompt with Terraform module information, ensuring the output code meets organizational best practices.
  6. Commits the generated Terraform configuration and the README to the GitHub repository, providing traceability and transparency.
  7. Responds with success, including URLs to the committed GitHub files, or returns detailed error information for troubleshooting.



#### Knowledge Base (KB)
- **Description**: A structured repository containing AWS service and Terraform module information.
- **Structure**: JSON format categorizing services and modules.
- **Configure Knowledge Base**: Configuring a Knowledge Base (KB) enables your Bedrock agents to access a repository of information for AWS account provisioning. Follow these steps to set up your KB:
  1. Access the Amazon Bedrock Console: Log in and go directly to the 'Knowledge Base' section. This is your starting point for creating a new KB.
  2. Name Your Knowledge Base: Choose a clear and descriptive name that reflects the purpose of your KB, such as "AWS Account Setup KB."
  3. Select an IAM Role: Assign a pre-configured IAM role with the necessary permissions. 
  4. Define the Data Source: Upload a JSON file to an S3 bucket with encryption enabled for security. This file should contain a structured list of Terraform modules. For the JSON structure, use the example provided in this repository
  5. Choose the Default Embeddings Model: For most use cases, the Amazon Bedrock Titan G1 Embeddings - Text model will suffice. It's pre-configured and ready to use, simplifying the process.
  6. Opt for the Managed Vector Store: Allow Amazon Bedrock to create and manage the vector store for you in Amazon OpenSearch Service.
  7. Review and Finalize: Double-check all entered information for accuracy. Pay special attention to the S3 bucket URI and IAM role details.

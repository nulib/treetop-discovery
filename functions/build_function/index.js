// @ts-check
const { execSync } = require("child_process");
const {
  AmplifyClient,
  StartDeploymentCommand,
  CreateDeploymentCommand,
} = require("@aws-sdk/client-amplify");
const zl = require("zip-lib");
const { readFileSync } = require("fs");

const amplifyClient = new AmplifyClient({});

/**
 * Uploads a ZIP file to the specified URL for deployment
 *
 * @param {string} zipFilePath
 * @param {string} zipUploadUrl
 */
async function uploadZipFile(zipFilePath, zipUploadUrl) {
  const zipFile = readFileSync(zipFilePath);

  const response = await fetch(zipUploadUrl, {
    method: "PUT",
    body: zipFile,
    headers: {
      "Content-Type": "application/zip",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to upload zip file: ${response?.statusText}`);
  }

  console.log("Response from upload:", response);

  return response;
}

/**
 * Fetch, build, and deploy the UI from source
 *
 * @param {any} event
 * @param {import("aws-lambda").Context} _context
 */
exports.handler = async (event, _context) => {
  try {
    const repoName = process.env.REPO_NAME;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const appId = process.env.AMPLIFY_APP_ID;
    // Because this function is not triggered by the API Gateway or another service,
    // we pass the branch name as an environment variable directly on the event.
    const branchName = event["AMPLIFY_BRANCH_NAME"] ?? process.env.AMPLIFY_BRANCH_NAME;

    if (!repoName) {
      throw new Error("REPO_NAME is not set in environment variables");
    }

    if (!apiUrl) {
      throw new Error("API_URL is not set in environment variables");
    }

    if (!appId) {
      throw new Error("AMPLIFY_APP_ID is not set in environment variables");
    }

    if (!branchName) {
      throw new Error("AMPLIFY_BRANCH_NAME is not set in environment variables");
    }

    execSync("rm -rf /tmp/*", { encoding: "utf8", stdio: "inherit" });

    execSync(`cd /tmp && git clone https://github.com/nulib/${repoName}.git`, {
      encoding: "utf8",
      stdio: "inherit",
    });

    process.env.NPM_CONFIG_CACHE = "/tmp/.npm"; // needed for npm to build in the lambda environment

    // /out is the nextjs output when config is set to "export"
    execSync(`cd /tmp/${repoName} && npm install && NEXT_PUBLIC_API_URL=${apiUrl} npm run build`, {
      encoding: "utf8",
      stdio: "inherit",
    });

    const deploymentZip = "/tmp/deployment.zip";
    await zl.archiveFolder(`/tmp/${repoName}/out`, deploymentZip).then(() => {
      console.log("Folder successfully zipped");
    });

    const createDeployment = new CreateDeploymentCommand({
      appId: appId,
      branchName: branchName,
    });
    const createDeploymentResponse = await amplifyClient.send(createDeployment);
    const { jobId, zipUploadUrl } = createDeploymentResponse;

    if (!zipUploadUrl || !jobId) {
      throw new Error("Failed to create deployment");
    }

    await uploadZipFile(deploymentZip, zipUploadUrl);

    const startDeploymentCommand = new StartDeploymentCommand({
      appId: appId,
      branchName: branchName,
      jobId,
      sourceUrl: zipUploadUrl,
    });
    const startDeploymentResponse = await amplifyClient.send(startDeploymentCommand);

    return {
      statusCode: 200,
      body: JSON.stringify({ status: startDeploymentResponse.jobSummary?.status || "unknown" }),
    };
  } catch (error) {
    console.error("Error:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ status: "failure" }),
    };
  }
};

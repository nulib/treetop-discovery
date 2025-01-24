// @ts-check
const { execSync } = require("child_process");
const { S3Client, PutObjectCommand } = require("@aws-sdk/client-s3");
const { join } = require("path");
const { readFile, readdir, stat } = require("fs/promises");

/**
 * @typedef {import("aws-lambda").CloudFormationCustomResourceResponse} ResourceResponse
 * @typedef {import("aws-lambda").CloudFormationCustomResourceEvent} ResourceEvent
 * @typedef {import("aws-lambda").Context} Context
 *
 */

const client = new S3Client({});

/**
 * Get the MIME type based on the file extension
 *
 * @param {string} fileName
 */
function getMimeTypeFromFileName(fileName) {
  const ext = fileName.split(".").pop();
  switch (ext) {
    case "css":
      return "text/css";
    case "js":
      return "text/javascript";
    case "json":
      return "application/json";
    case "html":
      return "text/html";
    case "png":
      return "image/png";
    case "jpg":
    case "jpeg":
      return "image/jpeg";
    case "gif":
      return "image/gif";
    case "svg":
      return "image/svg+xml";
    default:
      return "application/octet-stream";
  }
}

/**
 * Recursively copies a directory from /tmp to S3
 * @param {string} sourceDir - Local directory path in /tmp
 * @param {string} bucketName - S3 bucket name
 * @param {string} targetPrefix - Target prefix/path in S3
 */
async function copyDirectoryToS3(sourceDir, bucketName, targetPrefix = "") {
  try {
    console.log("copyDirectoryToS3...");
    // Ensure source dir starts with /tmp
    if (!sourceDir.startsWith("/tmp/")) {
      sourceDir = `/tmp/${sourceDir}`;
    }

    // Read all files in the directory
    const allFiles = await readdir(sourceDir, { recursive: true });
    console.log(`Files in directory: ${allFiles.length}`);

    // Filter out directories
    const filePromises = allFiles.map(async (file) => {
      const filePath = join(sourceDir, file);
      const stats = await stat(filePath);
      return { file, isFile: stats.isFile() };
    });

    const fileResults = await Promise.all(filePromises);
    const files = fileResults.filter((result) => result.isFile).map((result) => result.file);

    // Upload each file
    const uploadPromises = files.map(async (file) => {
      console.log("uploading file", file);
      const filePath = join(sourceDir, file);
      const fileContent = await readFile(filePath);

      // Construct the S3 key (path in bucket)
      const s3Key = targetPrefix ? `${targetPrefix}/${file}` : file;

      const uploadParams = {
        Bucket: bucketName,
        Key: s3Key,
        Body: fileContent,
        ContentType: getMimeTypeFromFileName(file),
      };

      try {
        await client.send(new PutObjectCommand(uploadParams));
        console.log(`Uploaded: ${file} to ${s3Key}`);
        return { file, success: true };
      } catch (error) {
        console.error(`Failed to upload ${file}:`, error);
        return { file, success: false, error: error.message };
      }
    });

    // Wait for all uploads to complete
    const results = await Promise.all(uploadPromises);

    return {
      success: true,
      message: "Directory upload completed",
      results: results,
    };
  } catch (error) {
    console.error("Error in directory upload:", error);
    throw {
      success: false,
      message: "Failed to upload directory",
      error: error.message,
    };
  }
}

/**
 * Function to fetch and build the UI from the source code
 *
 * @param {ResourceEvent} event
 * @param {Context} context
 * @remarks
 * NOTE: responses are not returned from the Lambda handler but rather they are sent to the event ResponseURL.
 */
exports.handler = async (event, context) => {
  console.log(event);

  try {
    const bucketName = process.env.BUCKET_NAME;
    const repoName = process.env.REPO_NAME;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    if (!bucketName) {
      throw new Error("BUCKET_NAME is not set in environment variables");
    }

    if (!repoName) {
      throw new Error("REPO_NAME is not set in environment variables");
    }

    if (!apiUrl) {
      throw new Error("API_URL is not set in environment variables");
    }

    // Pull repository from source
    execSync("rm -rf /tmp/*", { encoding: "utf8", stdio: "inherit" });

    execSync(`cd /tmp && git clone https://github.com/nulib/${repoName}.git`, {
      encoding: "utf8",
      stdio: "inherit",
    });

    // Build from source
    process.env.NPM_CONFIG_CACHE = "/tmp/.npm";
    execSync(`cd /tmp/${repoName} && npm install && NEXT_PUBLIC_API_URL=${apiUrl} npm run build`, {
      encoding: "utf8",
      stdio: "inherit",
    });

    // /out is the nextjs output when config is set to "export"
    const buildDir = `/tmp/${repoName}/out`;

    await copyDirectoryToS3(buildDir, bucketName);

    // Ensure response is sent in order to shut down custom event
    return {
      statusCode: 200,
      message: "Success",
    }
  } catch (error) {
    console.error("Error:", error);
    return {
      statusCode: 500,
      message: error.message,
    };
  }
};

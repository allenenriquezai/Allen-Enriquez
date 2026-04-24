import { S3Client, PutBucketCorsCommand } from "@aws-sdk/client-s3";
import * as dotenv from "dotenv";
import * as path from "path";

dotenv.config({ path: path.resolve(process.cwd(), ".env.local") });

const s3 = new S3Client({
  region: "auto",
  endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
  },
});

const cmd = new PutBucketCorsCommand({
  Bucket: process.env.R2_BUCKET_NAME!,
  CORSConfiguration: {
    CORSRules: [
      {
        AllowedOrigins: ["*"],
        AllowedMethods: ["GET", "PUT"],
        AllowedHeaders: ["*"],
        MaxAgeSeconds: 3600,
      },
    ],
  },
});

s3.send(cmd).then((res) => console.log("CORS set:", res.$metadata.httpStatusCode)).catch(console.error);

import {
  AwsCredentialIdentity,
  AwsCredentialIdentityProvider,
} from "@smithy/types";
import { AwsSdkCredentialsFeatures } from "../feature-ids";
export {
  AwsCredentialIdentity,
  AwsCredentialIdentityProvider,
  IdentityProvider,
} from "@smithy/types";
export interface AwsIdentityProperties {
  callerClientConfig?: {
    region(): Promise<string>;
    profile?: string;
    credentialDefaultProvider?: (input?: any) => AwsCredentialIdentityProvider;
  };
}
export type RuntimeConfigIdentityProvider<T> = (
  awsIdentityProperties?: AwsIdentityProperties
) => Promise<T>;
export type RuntimeConfigAwsCredentialIdentityProvider =
  RuntimeConfigIdentityProvider<AwsCredentialIdentity>;
export type AttributedAwsCredentialIdentity = AwsCredentialIdentity & {
  $source?: AwsSdkCredentialsFeatures;
};

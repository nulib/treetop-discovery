# build_function

A function triggered by a custom CloudFormation Event that build the OSDP UI from source.

## development

To most effectively make adjustments to this function, install the necessary dependencies.

If still in the root, change into this directory:

```bash
cd ./osdp-prototype/build_function
```

And install the dependencies:

```bash
npm i
```

## notes

If the function fails to send the response for some reason, the stack can get stuck in `CREATE_IN_PROGRESS` or `DELETE_IN_PROGRESS`.

You will need to send a response to the custom resource manually following instructions [here](https://repost.aws/knowledge-center/cloudformation-lambda-resource-delete)


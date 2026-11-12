#!/bin/sh
# Only LocalStack invokes this initializer. No AWS cloud provisioning commands.
set -eu
case "${LOCALSTACK_HOST:-localhost}" in localhost|localstack|localhost.localstack.cloud) ;; *) exit 1 ;; esac
if ! awslocal events describe-event-bus --name waypoint >/dev/null 2>&1; then
  awslocal events create-event-bus --name waypoint
fi
for consumer in operations identity notifications planning; do
  dlq=$(awslocal sqs create-queue --queue-name "$consumer-dlq" --query QueueUrl --output text)
  arn=$(awslocal sqs get-queue-attributes --queue-url "$dlq" --attribute-names QueueArn --query Attributes.QueueArn --output text)
  awslocal sqs create-queue --queue-name "$consumer" --attributes "{\"VisibilityTimeout\":\"120\",\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"$arn\\\",\\\"maxReceiveCount\\\":\\\"5\\\"}\"}"
done
for consumer in operations identity notifications; do
  case "$consumer" in
    operations) sources='["identity-access","network-fleet","operations","scheduler"]' ;;
    identity) sources='["network-fleet","operations"]' ;;
    notifications) sources='["operations"]' ;;
  esac
  awslocal events put-rule --event-bus-name waypoint --name "$consumer" --event-pattern "{\"source\":$sources}"
  url=$(awslocal sqs get-queue-url --queue-name "$consumer" --query QueueUrl --output text)
  arn=$(awslocal sqs get-queue-attributes --queue-url "$url" --attribute-names QueueArn --query Attributes.QueueArn --output text)
  awslocal events put-targets --event-bus-name waypoint --rule "$consumer" --targets "Id=$consumer,Arn=$arn"
done
if ! awslocal s3api head-bucket --bucket waypoint-private-proofs >/dev/null 2>&1; then
  awslocal s3 mb s3://waypoint-private-proofs
fi
awslocal s3api put-public-access-block --bucket waypoint-private-proofs --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

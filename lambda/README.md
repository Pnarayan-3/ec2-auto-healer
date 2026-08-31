# AWS Lambda — EC2 Auto-Healer

This Lambda function acts as the **incident response and recovery component** of the EC2 Auto-Healer project.

It is triggered when the CloudWatch health alarm enters the `ALARM` state through an Amazon EventBridge rule.

## 🔄 Recovery Workflow

```text
CloudWatch Alarm
       ↓
EventBridge
       ↓
AWS Lambda
       ↓
Check EC2 State
       ↓
Restart Nginx using SSM
       ↓
 ┌─────┴─────┐
 │           │
Success     Failed
 │           │
 ▼           ▼
SNS       EC2 Reboot
Alert         │
              ▼
             SNS
```

## 🛠️ Responsibilities

The Lambda function:

1. Receives the CloudWatch alarm event.
2. Identifies the target EC2 instance.
3. Checks the current EC2 instance state.
4. Attempts to restart Nginx using AWS Systems Manager.
5. Checks the SSM command result.
6. If service recovery succeeds, sends an SNS notification.
7. If service recovery fails, reboots the EC2 instance.
8. Sends an SNS notification describing the recovery action.
9. Logs the recovery workflow to CloudWatch Logs.

## ⚙️ Environment Variables

The Lambda function requires the following environment variables:

| Variable        | Description                                 |
| --------------- | ------------------------------------------- |
| `INSTANCE_ID`   | ID of the EC2 instance to recover           |
| `SNS_TOPIC_ARN` | ARN of the SNS topic used for notifications |

Example:

```text
INSTANCE_ID = i-xxxxxxxxxxxxxxxxx
SNS_TOPIC_ARN = arn:aws:sns:region:account-id:topic-name
```

Do not hard-code these values into the Python source code.

## 🔐 Required IAM Permissions

The Lambda execution role requires permissions for:

```text
ec2:DescribeInstances
ec2:RebootInstances

ssm:SendCommand
ssm:GetCommandInvocation

sns:Publish

cloudwatch:PutMetricData
```

The exact IAM policy should be restricted to the required resources in a production environment.

## 📦 Runtime

```text
Runtime: Python 3.x
```

The function uses:

```python
boto3
```

which is available in the standard AWS Lambda Python runtime.

## 📄 Main File

The Lambda implementation is located at:

```text
lambda_function.py
```

## 🧪 Testing

The recovery workflow can be tested by intentionally stopping Nginx on the monitored EC2 instance:

```bash
sudo systemctl stop nginx
```

The Bash health-check script should detect the failure and publish the corresponding CloudWatch metric.

After the CloudWatch alarm enters `ALARM` state:

```text
CloudWatch
    ↓
EventBridge
    ↓
Lambda
    ↓
SSM
    ↓
Nginx Recovery
```

If the service recovery fails:

```text
Lambda
    ↓
EC2 Reboot
```

The final recovery status is reported through SNS.

## 📊 Logging

Lambda execution logs are available in:

```text
Amazon CloudWatch Logs
```

The logs include:

* EC2 instance state
* Recovery type
* SSM command ID
* SSM command status
* Recovery actions
* Errors and exceptions

## 🎯 Purpose

This Lambda function demonstrates **event-driven incident response and automated infrastructure recovery** using AWS serverless services.

import json
import os
import time

import boto3


ec2 = boto3.client("ec2")
ssm = boto3.client("ssm")
sns = boto3.client("sns")
cloudwatch = boto3.client("cloudwatch")


INSTANCE_ID = os.environ["INSTANCE_ID"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def send_notification(subject, message)

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=subject,
        Message=message
    )

def record_recovery_attempt(recovery_type):

    cloudwatch.put_metric_data(
        Namespace="EC2AutoHealer",
        MetricData=[
            {
                "MetricName": "RecoveryAttempt",
                "Dimensions": [
                    {
                        "Name": "InstanceId",
                        "Value": INSTANCE_ID
                    },
                    {
                        "Name": "RecoveryType",
                        "Value": recovery_type
                    }
                ],
                "Value": 1,
                "Unit": "Count"
            }
        ]
    )

    print(f"Recovery metric published: {recovery_type}")

def restart_nginx():

    print("Attempting service-level recovery...")

    response = ssm.send_command(
        InstanceIds=[INSTANCE_ID],
        DocumentName="AWS-RunShellScript",
        Parameters={
            "commands": [
                "systemctl restart nginx",
                "systemctl is-active --quiet nginx"
            ]
        }
    )

    command_id = response["Command"]["CommandId"]

    print(f"SSM command ID: {command_id}")

    return command_id


def check_command(command_id):

    print("Waiting for SSM command result...")

    for _ in range(10):

        time.sleep(5)

        response = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=INSTANCE_ID
        )

        status = response["Status"]

        print(f"SSM command status: {status}")

        if status in [
            "Success",
            "Failed",
            "TimedOut",
            "Cancelled"
        ]:
            return status

    return "TimedOut"


def reboot_instance():

    print("Service recovery failed.")
    print("Escalating to EC2 reboot.")

    ec2.reboot_instances(
        InstanceIds=[INSTANCE_ID]
    )

    return "EC2 reboot initiated"


def lambda_handler(event, context):

    print("====================================")
    print("       EC2 AUTO-HEALER INCIDENT")
    print("====================================")

    print(f"Instance: {INSTANCE_ID}")
    print("Recovery workflow started")

    print("Received event:")
    print(json.dumps(event))

    try:

        # Check EC2 state
        response = ec2.describe_instances(
            InstanceIds=[INSTANCE_ID]
        )

        instance = response["Reservations"][0]["Instances"][0]

        state = instance["State"]["Name"]

        print(f"Current EC2 state: {state}")

        if state != "running":

            action = (
                f"Instance is currently {state}. "
                f"No service-level recovery attempted."
            )

            send_notification(
                "EC2 Auto-Healer - Recovery Skipped",
                action
            )

            return {
                "statusCode": 200,
                "body": action
            }

        # Stage 1: Nginx service recovery
        print("Recovery type: SERVICE")
        print("Action: Restart Nginx")
        record_recovery_attempt("SERVICE")
        command_id = restart_nginx()

        command_status = check_command(command_id)

        if command_status == "Success":

            message = f"""
EC2 AUTO-HEALER

Instance:
{INSTANCE_ID}

Incident:
Nginx service failure detected.

Recovery:
Nginx restart successful.

Action:
Service-level recovery completed.

EC2 reboot:
Not required.
"""

            send_notification(
                "EC2 Auto-Healer - Service Recovered",
                message
            )

            print(message)

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "recovery": "service",
                    "status": "success"
                })
            }

        # Stage 2: Infrastructure recovery
        print("Recovery type: INFRASTRUCTURE")
        print("Action: Reboot EC2")

        record_recovery_attempt("INFRASTRUCTURE")
        action = reboot_instance()

        message = f"""
EC2 AUTO-HEALER

Instance:
{INSTANCE_ID}

Incident:
Nginx service recovery failed.

Stage 1:
Nginx restart unsuccessful.

Stage 2:
EC2 infrastructure recovery triggered.

Action:
{action}
"""

        send_notification(
            "EC2 Auto-Healer - Escalated Recovery",
            message
        )

        print(message)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "recovery": "ec2_reboot",
                "status": "initiated"
            })
        }

    except Exception as error:

        print(f"Recovery workflow failed: {error}")

        error_message = f"""
EC2 AUTO-HEALER FAILURE

Instance:
{INSTANCE_ID}

The automated recovery workflow encountered an error.

Error:
{error}
"""

        send_notification(
            "EC2 Auto-Healer - Recovery FAILED",
            error_message
        )

        raise
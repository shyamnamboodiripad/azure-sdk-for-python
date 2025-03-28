# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
DESCRIPTION:
    This sample demonstrates how to use basic agent operations from
    the Azure Agents service using a synchronous client with tracing to console and adding
    custom attributes to the span.

USAGE:
    python sample_agents_basics_with_console_tracing_custom_attributes.py

    Before running the sample:

    pip install azure-ai-projects azure-identity opentelemetry-sdk azure-core-tracing-opentelemetry

    If you want to export telemetry to OTLP endpoint (such as Aspire dashboard
    https://learn.microsoft.com/dotnet/aspire/fundamentals/dashboard/standalone?tabs=bash)
    install:

    pip install opentelemetry-exporter-otlp-proto-grpc

    Set these environment variables with your own values:
    1) PROJECT_CONNECTION_STRING - The project connection string, as found in the overview page of your
       Azure AI Foundry project.
    2) MODEL_DEPLOYMENT_NAME - The deployment name of the AI model, as found under the "Name" column in 
       the "Models + endpoints" tab in your Azure AI Foundry project.
    3) AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED - Optional. Set to `true` to trace the content of chat
       messages, which may contain personal data. False by default.
"""

import os, sys, time
from typing import cast
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan, Span, TracerProvider


# Define the custom span processor that is used for adding the custom
# attributes to spans when they are started.
class CustomAttributeSpanProcessor(SpanProcessor):
    def __init__(self):
        pass

    def on_start(self, span: Span, parent_context=None):
        # Add this attribute to all spans
        span.set_attribute("trace_sample.sessionid", "123")

        # Add another attribute only to create_message spans
        if span.name == "create_message":
            span.set_attribute("trace_sample.message.context", "abc")

    def on_end(self, span: ReadableSpan):
        # Clean-up logic can be added here if necessary
        pass


project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["PROJECT_CONNECTION_STRING"],
)

# Enable console tracing
# or, if you have local OTLP endpoint running, change it to
# project_client.telemetry.enable(destination="http://localhost:4317")
project_client.telemetry.enable(destination=sys.stdout)

# Add the custom span processor to the global tracer provider
provider = cast(TracerProvider, trace.get_tracer_provider())
provider.add_span_processor(CustomAttributeSpanProcessor())

scenario = os.path.basename(__file__)
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span(scenario):
    with project_client:
        agent = project_client.agents.create_agent(
            model=os.environ["MODEL_DEPLOYMENT_NAME"], name="my-assistant", instructions="You are helpful assistant"
        )
        print(f"Created agent, agent ID: {agent.id}")

        thread = project_client.agents.create_thread()
        print(f"Created thread, thread ID: {thread.id}")

        message = project_client.agents.create_message(
            thread_id=thread.id, role="user", content="Hello, tell me a joke"
        )
        print(f"Created message, message ID: {message.id}")

        run = project_client.agents.create_run(thread_id=thread.id, agent_id=agent.id)

        # Poll the run as long as run status is queued or in progress
        while run.status in ["queued", "in_progress", "requires_action"]:
            # Wait for a second
            time.sleep(1)
            run = project_client.agents.get_run(thread_id=thread.id, run_id=run.id)

            print(f"Run status: {run.status}")

        project_client.agents.delete_agent(agent.id)
        print("Deleted agent")

        messages = project_client.agents.list_messages(thread_id=thread.id)
        print(f"messages: {messages}")

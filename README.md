# Multiagent ASP MCP Agent

## Installation

You can install this package using pip. From the root of the repository, run:

```bash
pip install .
```

Or, for development mode (recommended for contributors):

```bash
pip install -e .
```

## Environment Variables

Some tools and server components require environment variables to be set.

```bash
AZURE_OPENAI_KEY=your-key-here
AZURE_ENDPOINT=your-endpoint-here
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_MODEL=gpt-4.1
AZURE_OPENAI_API_VERSION=2025-01-01-preview
```
Newer models will probably work too.


## Usage

After installation, you can start the client from the command line:

```bash
asp-llm-client [input_file]
```

You can either give a description of your problem or type it by hand.
The llm will try to generate your encoding with an example instance,
and test every constraint given using a python program.
Encodings are extended gradually, they can be saved to disk in the end (just ask for it).
The history of the llm is cleaned up from time to time to improve quality.
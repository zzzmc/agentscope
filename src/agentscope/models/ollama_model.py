# -*- coding: utf-8 -*-
"""Model wrapper for Ollama models."""
from abc import ABC
from typing import Sequence, Any, Optional, List, Union, Generator

from ..message import Msg
from ..models import ModelWrapperBase, ModelResponse
from ..utils.common import _convert_to_str


class OllamaWrapperBase(ModelWrapperBase, ABC):
    """The base class for Ollama model wrappers.

    To use Ollama API, please
    1. First install ollama server from https://ollama.com/download and
    start the server
    2. Pull the model by `ollama pull {model_name}` in terminal
    After that, you can use the ollama API.
    """

    model_type: str
    """The type of the model wrapper, which is to identify the model wrapper
    class in model configuration."""

    model_name: str
    """The model name used in ollama API."""

    options: dict
    """A dict contains the options for ollama generation API,
    e.g. {"temperature": 0, "seed": 123}"""

    keep_alive: str
    """Controls how long the model will stay loaded into memory following
    the request."""

    def __init__(
        self,
        config_name: str,
        model_name: str,
        options: dict = None,
        keep_alive: str = "5m",
        host: Optional[Union[str, None]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the model wrapper for Ollama API.

        Args:
            model_name (`str`):
                The model name used in ollama API.
            options (`dict`, default `None`):
                The extra keyword arguments used in Ollama api generation,
                e.g. `{"temperature": 0., "seed": 123}`.
            keep_alive (`str`, default `5m`):
                Controls how long the model will stay loaded into memory
                following the request.
            host (`str`, default `None`):
                The host port of the ollama server.
                Defaults to `None`, which is 127.0.0.1:11434.
        """

        super().__init__(config_name=config_name, model_name=model_name)

        self.options = options
        self.keep_alive = keep_alive

        try:
            import ollama
        except ImportError as e:
            raise ImportError(
                "The package ollama is not found. Please install it by "
                'running command `pip install "ollama>=0.1.7"`',
            ) from e

        self.client = ollama.Client(host=host, **kwargs)


class OllamaChatWrapper(OllamaWrapperBase):
    """The model wrapper for Ollama chat API.

    Response:
        - Refer to
        https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion

        ```json
        {
            "model": "registry.ollama.ai/library/llama3:latest",
            "created_at": "2023-12-12T14:13:43.416799Z",
            "message": {
                "role": "assistant",
                "content": "Hello! How are you today?"
            },
            "done": true,
            "total_duration": 5191566416,
            "load_duration": 2154458,
            "prompt_eval_count": 26,
            "prompt_eval_duration": 383809000,
            "eval_count": 298,
            "eval_duration": 4799921000
        }
        ```
    """

    model_type: str = "ollama_chat"

    def __init__(
        self,
        config_name: str,
        model_name: str,
        stream: bool = False,
        options: dict = None,
        keep_alive: str = "5m",
        host: Optional[Union[str, None]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the model wrapper for Ollama API.

        Args:
            model_name (`str`):
                The model name used in ollama API.
            stream (`bool`, default `False`):
                Whether to enable stream mode.
            options (`dict`, default `None`):
                The extra keyword arguments used in Ollama api generation,
                e.g. `{"temperature": 0., "seed": 123}`.
            keep_alive (`str`, default `5m`):
                Controls how long the model will stay loaded into memory
                following the request.
            host (`str`, default `None`):
                The host port of the ollama server.
                Defaults to `None`, which is 127.0.0.1:11434.
        """

        super().__init__(
            config_name=config_name,
            model_name=model_name,
            options=options,
            keep_alive=keep_alive,
            host=host,
            **kwargs,
        )

        self.stream = stream

    def __call__(
        self,
        messages: Sequence[dict],
        stream: Optional[bool] = None,
        options: Optional[dict] = None,
        keep_alive: Optional[str] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate response from the given messages.

        Args:
            messages (`Sequence[dict]`):
                A list of messages, each message is a dict contains the `role`
                and `content` of the message.
            stream (`bool`, default `None`):
                Whether to enable stream mode, which will override the `stream`
                input in the constructor.
            options (`dict`, default `None`):
                The extra arguments used in ollama chat API, which takes
                effect only on this call, and will be merged with the
                `options` input in the constructor,
                e.g. `{"temperature": 0., "seed": 123}`.
            keep_alive (`str`, default `None`):
                How long the model will stay loaded into memory following
                the request, which takes effect only on this call, and will
                override the `keep_alive` input in the constructor.

        Returns:
            `ModelResponse`:
                The response text in `text` field, and the raw response in
                `raw` field.
        """
        # step1: prepare parameters accordingly
        if options is None:
            options = self.options
        else:
            options = {**self.options, **options}

        keep_alive = keep_alive or self.keep_alive

        # step2: forward to generate response
        if stream is None:
            stream = self.stream

        kwargs.update(
            {
                "model": self.model_name,
                "messages": messages,
                "stream": stream,
                "options": options,
                "keep_alive": keep_alive,
            },
        )

        response = self.client.chat(**kwargs)

        if stream:

            def generator() -> Generator[str, None, None]:
                last_chunk = {}
                text = ""
                for chunk in response:
                    text += chunk["message"]["content"]
                    yield text
                    last_chunk = chunk

                # Replace the last chunk with the full text
                last_chunk["message"]["content"] = text

                self._save_model_invocation_and_update_monitor(
                    kwargs,
                    last_chunk,
                )

            return ModelResponse(
                stream=generator(),
                raw=response,
            )

        else:
            # step3: save model invocation and update monitor
            self._save_model_invocation_and_update_monitor(
                kwargs,
                response,
            )

            # step4: return response
            return ModelResponse(
                text=response["message"]["content"],
                raw=response,
            )

    def _save_model_invocation_and_update_monitor(
        self,
        kwargs: dict,
        response: dict,
    ) -> None:
        """Save the model invocation and update the monitor accordingly.

        Args:
            kwargs (`dict`):
                The keyword arguments to the DashScope chat API.
            response (`dict`):
                The response object returned by the DashScope chat API.
        """
        prompt_eval_count = response.get("prompt_eval_count", 0)
        eval_count = response.get("eval_count", 0)

        self.monitor.update_text_and_embedding_tokens(
            model_name=self.model_name,
            prompt_tokens=prompt_eval_count,
            completion_tokens=eval_count,
        )

        self._save_model_invocation(
            arguments=kwargs,
            response=response,
        )

    def format(
        self,
        *args: Union[Msg, Sequence[Msg]],
    ) -> List[dict]:
        """Format the messages for ollama Chat API.

        All messages will be formatted into a single system message with
        system prompt and conversation history.

        Note:
        1. This strategy maybe not suitable for all scenarios,
        and developers are encouraged to implement their own prompt
        engineering strategies.
        2. For ollama chat api, the content field shouldn't be empty string.

        Example:

        .. code-block:: python

            prompt = model.format(
                Msg("system", "You're a helpful assistant", role="system"),
                Msg("Bob", "Hi, how can I help you?", role="assistant"),
                Msg("user", "What's the date today?", role="user")
            )

        The prompt will be as follows:

        .. code-block:: python

            [
                {
                    "role": "system",
                    "content": "You're a helpful assistant"
                },
                {
                    "role": "user",
                    "content": (
                        "## Conversation History\\n"
                        "Bob: Hi, how can I help you?\\n"
                        "user: What's the date today?"
                    )
                }
            ]


        Args:
            args (`Union[Msg, Sequence[Msg]]`):
                The input arguments to be formatted, where each argument
                should be a `Msg` object, or a list of `Msg` objects.
                In distribution, placeholder is also allowed.

        Returns:
            `List[dict]`:
                The formatted messages.
        """

        # Parse all information into a list of messages
        input_msgs = []
        for _ in args:
            if _ is None:
                continue
            if isinstance(_, Msg):
                input_msgs.append(_)
            elif isinstance(_, list) and all(isinstance(__, Msg) for __ in _):
                input_msgs.extend(_)
            else:
                raise TypeError(
                    f"The input should be a Msg object or a list "
                    f"of Msg objects, got {type(_)}.",
                )

        # record dialog history as a list of strings
        system_prompt = None
        history_content_template = []
        dialogue = []
        # TODO: here we default the url links to images
        images = []
        for i, unit in enumerate(input_msgs):
            if i == 0 and unit.role == "system":
                # system prompt
                system_prompt = _convert_to_str(unit.content)
            else:
                # Merge all messages into a conversation history prompt
                dialogue.append(
                    f"{unit.name}: {_convert_to_str(unit.content)}",
                )

            if unit.url is not None:
                images.append(unit.url)

        if len(dialogue) != 0:
            dialogue_history = "\n".join(dialogue)

            history_content_template.extend(
                ["## Conversation History", dialogue_history],
            )

        history_content = "\n".join(history_content_template)

        # The conversation history message
        history_message = {
            "role": "user",
            "content": history_content,
        }

        if len(images) != 0:
            history_message["images"] = images

        if system_prompt is None:
            return [history_message]

        return [
            {"role": "system", "content": system_prompt},
            history_message,
        ]


class OllamaEmbeddingWrapper(OllamaWrapperBase):
    """The model wrapper for Ollama embedding API.

    Response:
        - Refer to
        https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings

        ```json
        {
            "model": "all-minilm",
            "embeddings": [[
                0.010071029, -0.0017594862, 0.05007221, 0.04692972,
                0.008599704, 0.105441414, -0.025878139, 0.12958129,
            ]]
        }
        ```
    """

    model_type: str = "ollama_embedding"

    def __call__(
        self,
        prompt: str,
        options: Optional[dict] = None,
        keep_alive: Optional[str] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate embedding from the given prompt.

        Args:
            prompt (`str`):
                The prompt to generate response.
            options (`dict`, default `None`):
                The extra arguments used in ollama embedding API, which takes
                effect only on this call, and will be merged with the
                `options` input in the constructor,
                e.g. `{"temperature": 0., "seed": 123}`.
            keep_alive (`str`, default `None`):
                How long the model will stay loaded into memory following
                the request, which takes effect only on this call, and will
                override the `keep_alive` input in the constructor.

        Returns:
            `ModelResponse`:
                The response embedding in `embedding` field, and the raw
                response in `raw` field.
        """
        # step1: prepare parameters accordingly
        if options is None:
            options = self.options
        else:
            options = {**self.options, **options}

        keep_alive = keep_alive or self.keep_alive

        # step2: forward to generate response
        response = self.client.embeddings(
            model=self.model_name,
            prompt=prompt,
            options=options,
            keep_alive=keep_alive,
            **kwargs,
        )

        # step3: record the api invocation if needed
        self._save_model_invocation(
            arguments={
                "model": self.model_name,
                "prompt": prompt,
                "options": options,
                "keep_alive": keep_alive,
                **kwargs,
            },
            response=response,
        )

        # step4: monitor the response
        self.monitor.update_text_and_embedding_tokens(
            model_name=self.model_name,
        )

        # step5: return response
        return ModelResponse(
            embedding=[response["embedding"]],
            raw=response,
        )

    def format(
        self,
        *args: Union[Msg, Sequence[Msg]],
    ) -> Union[List[dict], str]:
        raise RuntimeError(
            f"Model Wrapper [{type(self).__name__}] doesn't "
            f"need to format the input. Please try to use the "
            f"model wrapper directly.",
        )


class OllamaGenerationWrapper(OllamaWrapperBase):
    """The model wrapper for Ollama generation API.

    Response:
        - From
        https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-completion

        ```json
        {
            "model": "llama3",
            "created_at": "2023-08-04T19:22:45.499127Z",
            "response": "The sky is blue because it is the color of the sky.",
            "done": true,
            "context": [1, 2, 3],
            "total_duration": 5043500667,
            "load_duration": 5025959,
            "prompt_eval_count": 26,
            "prompt_eval_duration": 325953000,
            "eval_count": 290,
            "eval_duration": 4709213000
        }
        ```
    """

    model_type: str = "ollama_generate"

    def __call__(
        self,
        prompt: str,
        options: Optional[dict] = None,
        keep_alive: Optional[str] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate response from the given prompt.

        Args:
            prompt (`str`):
                The prompt to generate response.
            options (`dict`, default `None`):
                The extra arguments used in ollama generation API, which takes
                effect only on this call, and will be merged with the
                `options` input in the constructor,
                e.g. `{"temperature": 0., "seed": 123}`.
            keep_alive (`str`, default `None`):
                How long the model will stay loaded into memory following
                the request, which takes effect only on this call, and will
                override the `keep_alive` input in the constructor.

        Returns:
            `ModelResponse`:
                The response text in `text` field, and the raw response in
                `raw` field.

        """
        # step1: prepare parameters accordingly
        if options is None:
            options = self.options
        else:
            options = {**self.options, **options}

        keep_alive = keep_alive or self.keep_alive

        # step2: forward to generate response
        response = self.client.generate(
            model=self.model_name,
            prompt=prompt,
            options=options,
            keep_alive=keep_alive,
        )

        # step3: record the api invocation if needed
        self._save_model_invocation(
            arguments={
                "model": self.model_name,
                "prompt": prompt,
                "options": options,
                "keep_alive": keep_alive,
                **kwargs,
            },
            response=response,
        )

        # step4: monitor the response
        self.monitor.update_text_and_embedding_tokens(
            model_name=self.model_name,
            prompt_tokens=response.get("prompt_eval_count", 0),
            completion_tokens=response.get("eval_count", 0),
        )

        # step5: return response
        return ModelResponse(
            text=response["response"],
            raw=response,
        )

    def format(self, *args: Union[Msg, Sequence[Msg]]) -> str:
        """Forward the input to the model.

        Args:
            args (`Union[Msg, Sequence[Msg]]`):
                The input arguments to be formatted, where each argument
                should be a `Msg` object, or a list of `Msg` objects.
                In distribution, placeholder is also allowed.

        Returns:
            `str`:
                The formatted string prompt.
        """
        input_msgs = []
        for _ in args:
            if _ is None:
                continue
            if isinstance(_, Msg):
                input_msgs.append(_)
            elif isinstance(_, list) and all(isinstance(__, Msg) for __ in _):
                input_msgs.extend(_)
            else:
                raise TypeError(
                    f"The input should be a Msg object or a list "
                    f"of Msg objects, got {type(_)}.",
                )

        sys_prompt = None
        dialogue = []
        for i, unit in enumerate(input_msgs):
            if i == 0 and unit.role == "system":
                # system prompt
                sys_prompt = _convert_to_str(unit.content)
            else:
                # Merge all messages into a conversation history prompt
                dialogue.append(
                    f"{unit.name}: {_convert_to_str(unit.content)}",
                )

        dialogue_history = "\n".join(dialogue)

        if sys_prompt is None:
            prompt_template = "## Conversation History\n{dialogue_history}"
        else:
            prompt_template = (
                "{system_prompt}\n"
                "\n"
                "## Conversation History\n"
                "{dialogue_history}"
            )

        return prompt_template.format(
            system_prompt=sys_prompt,
            dialogue_history=dialogue_history,
        )

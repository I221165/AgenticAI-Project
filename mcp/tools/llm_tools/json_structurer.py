import json
import os
import re
from pydantic import BaseModel, Field, ValidationError
from langchain_community.chat_models import ChatOllama
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from ...base_tool import BaseAgenticTool


class JsonStructurerArgs(BaseModel):
    raw_text: str = Field(..., description="The raw text to be parsed into JSON")
    target_schema_name: str = Field(..., description="The Pydantic schema to target (e.g., 'ScriptOutput')")
    model_name: str = Field("llama3", description="The model name to use for formatting")
    provider: int = Field(2, description="1 for local (Ollama), 2 for cloud (Groq)")


class JsonStructurerTool(BaseAgenticTool):
    name = "json_structurer"
    description = "Formats unstructured text into strict JSON adhering to a specific Pydantic schema."
    args_schema = JsonStructurerArgs

    def execute(
        self,
        raw_text: str,
        target_schema_name: str,
        model_name: str = "llama3",
        provider: int = 2,
    ) -> dict:
        from shared.schemas.state_schema import StoryOutput, CharacterRoster, ScriptOutput

        schema_map = {
            "StoryOutput": StoryOutput,
            "CharacterRoster": CharacterRoster,
            "ScriptOutput": ScriptOutput,
        }
        if target_schema_name not in schema_map:
            raise ValueError(f"Unknown schema name: {target_schema_name}")

        target_class = schema_map[target_schema_name]

        # ----------------------------------------------------------------
        # Step 1: Try direct JSON parsing — skip LLM if raw_text is
        # already valid JSON that satisfies the schema.
        # ----------------------------------------------------------------
        direct = self._try_direct_parse(raw_text, target_class)
        if direct is not None:
            print(f"[JsonStructurer] Direct parse succeeded for {target_schema_name}")
            return direct

        # ----------------------------------------------------------------
        # Step 2: LLM-based structuring with retry
        # ----------------------------------------------------------------
        if provider == 1:
            ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
            print(f"[JsonStructurer] Ollama → {ollama_model}")
            try:
                from langchain_ollama import ChatOllama as ChatOllamaNew
                llm = ChatOllamaNew(model=ollama_model, temperature=0.1, format="json")
            except ImportError:
                llm = ChatOllama(model=ollama_model, temperature=0.1, format="json")
            # Small models get a concrete example prompt — schema instructions confuse them
            prompt = self._build_ollama_prompt(raw_text, target_schema_name)
        elif provider == 2:
            llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)
            parser = PydanticOutputParser(pydantic_object=target_class)
            prompt = (
                f"You are a strict JSON formatter. Extract and output ONLY a JSON object "
                f"matching this schema:\n\n{parser.get_format_instructions()}\n\n"
                f"Rules: output raw JSON only, no markdown, no extra keys.\n\n"
                f"Source text:\n{raw_text}"
            )
        else:
            raise ValueError("Invalid provider. Use 1 (Ollama) or 2 (Groq).")

        last_error = None
        for attempt in range(3):
            try:
                response = llm.invoke([
                    SystemMessage(content="Output raw JSON only. No markdown. No explanation."),
                    HumanMessage(content=prompt),
                ])
                if not response or not response.content:
                    raise RuntimeError("LLM returned an empty response")
                content = self._repair_unicode_escapes(self._clean_content(response.content))

                result = self._try_direct_parse(content, target_class)
                if result is not None:
                    return result

                if provider == 2:
                    parser = PydanticOutputParser(pydantic_object=target_class)
                    parsed = parser.parse(content)
                    return parsed.model_dump()

                raise RuntimeError(f"Could not parse response into {target_schema_name}")

            except Exception as e:
                last_error = e
                print(f"[JsonStructurer] Attempt {attempt + 1} failed: {e}")

        raise RuntimeError(
            f"Failed to structure {target_schema_name} after 3 attempts. "
            f"Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_ollama_prompt(self, raw_text: str, schema_name: str) -> str:
        """
        Concrete-example prompt for small local models.
        PydanticOutputParser schema instructions confuse sub-8B models —
        they output the schema itself instead of filling it in.
        A flat example with real placeholder values works much better.
        """
        examples = {
            "StoryOutput": (
                '{"title": "Story Title Here", "logline": "One sentence summary.", '
                '"themes": ["theme one", "theme two"], '
                '"narrative_arc": "Intro: setup. Climax: turning point. Resolution: ending."}'
            ),
            "CharacterRoster": (
                '{"characters": [{"name": "Character Name", "role": "Protagonist", '
                '"voice_personality": "calm, thoughtful male voice", '
                '"visual_description": "tall man with dark hair and a worn jacket"}]}'
            ),
            "ScriptOutput": (
                '{"scenes": [{"scene_id": "scene_1", "setting": "A dusty alleyway at night", '
                '"visual_description": "Neon signs reflect off wet pavement, shadows everywhere", '
                '"tone": "tense", "duration_estimate_sec": 20, '
                '"dialogue_lines": [{"character_name": "Alex", "text": "We need to move.", "emotion": "urgent"}]}]}'
            ),
        }
        example = examples.get(schema_name, "{}")
        return (
            f"Extract information from the text below and output ONLY a JSON object "
            f"in exactly this format (fill in real values from the text):\n\n"
            f"{example}\n\n"
            f"Text to extract from:\n{raw_text}\n\n"
            f"Output the JSON object only. No explanation. No markdown."
        )

    def _clean_content(self, text) -> str:
        """Strip markdown code fences from LLM output. Returns empty string for None."""
        if not text:
            return ""
        text = str(text).strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def _repair_unicode_escapes(self, text: str) -> str:
        """Zero-pad truncated \\uXX or \\uXXX escapes to the required 4 hex digits."""
        return re.sub(
            r'\\u([0-9a-fA-F]{1,3})(?![0-9a-fA-F])',
            lambda m: '\\u' + m.group(1).zfill(4),
            text,
        )

    def _try_direct_parse(self, text: str, target_class) -> dict | None:
        """
        Try to parse text as JSON and validate against target_class.
        Returns model_dump() on success, None on any failure.
        Handles cases where the JSON has extra keys (e.g. 'characters'
        alongside 'scenes') by passing only the fields the schema needs.
        """
        content = self._clean_content(text)

        # Find the outermost JSON object in the text (handles prose around it)
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None

        raw = match.group()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Repair truncated \uXX escapes (LLMs sometimes emit \u20 instead of  )
            repaired = self._repair_unicode_escapes(raw)
            try:
                data = json.loads(repaired)
            except json.JSONDecodeError:
                # Last resort: add closing bracket
                try:
                    data = json.loads(repaired + "}")
                except Exception:
                    return None

        if not isinstance(data, dict):
            return None

        schema_fields = target_class.model_fields.keys()

        # Small models often output {"properties": {"title": ..., "logline": ...}}
        # instead of {"title": ..., "logline": ...} — rescue values from inside properties
        if "properties" in data and isinstance(data["properties"], dict):
            props = data["properties"]
            if any(k in props for k in schema_fields):
                filtered = {k: v for k, v in props.items() if k in schema_fields}
                try:
                    return target_class(**filtered).model_dump()
                except (ValidationError, Exception):
                    pass

        # Normal path: filter to schema fields and validate
        filtered = {k: v for k, v in data.items() if k in schema_fields}
        try:
            obj = target_class(**filtered)
            return obj.model_dump()
        except (ValidationError, Exception):
            return None

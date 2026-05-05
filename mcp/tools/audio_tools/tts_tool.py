import os
import asyncio
from pydantic import BaseModel, Field
from typing import Optional
from ...base_tool import BaseAgenticTool


class TTSToolArgs(BaseModel):
    text: str = Field(..., description="The dialogue text to convert to speech.")
    character_name: str = Field(..., description="The name of the character speaking.")
    voice_personality: str = Field(..., description="The voice personality/description or ElevenLabs voice ID.")
    emotion: str = Field(..., description="The emotion the character is feeling.")
    output_dir: str = Field("assets/audio/dialogue", description="Directory to save the generated audio file.")
    provider: int = Field(4, description="1=Coqui (local), 2=ElevenLabs (paid), 3=gTTS (free/basic), 4=Edge-TTS (free/high-quality).")
    language: str = Field("English", description="Language for TTS synthesis.")


class TTSTool(BaseAgenticTool):
    name = "tts_generator"
    description = "Generates text-to-speech audio. Supports Edge-TTS (free), ElevenLabs (paid), gTTS (free/basic), Coqui (local)."
    args_schema = TTSToolArgs

    # English — full variety of Edge Neural voices
    EDGE_VOICES = {
        # Male voices
        "male_deep":          "en-US-GuyNeural",
        "male_confident":     "en-GB-RyanNeural",
        "male_young":         "en-US-ChristopherNeural",
        "male_narrator":      "en-US-SteffanNeural",
        "male_old":           "en-US-EricNeural",
        "male_british":       "en-GB-ThomasNeural",
        "male_energetic":     "en-US-AndrewNeural",
        # Female voices
        "female_warm":        "en-US-JennyNeural",
        "female_energetic":   "en-US-AriaNeural",
        "female_young":       "en-US-AriaNeural",
        "female_mature":      "en-US-EmmaNeural",
        "female_professional":"en-US-EmmaNeural",
        "female_british":     "en-GB-SoniaNeural",
        "female_soft":        "en-US-MichelleNeural",
    }

    # Non-English languages — one male + one female voice each
    LANG_VOICES = {
        "Urdu":    {"male": "ur-PK-AsadNeural",    "female": "ur-PK-UzmaNeural"},
        "Arabic":  {"male": "ar-SA-HamedNeural",   "female": "ar-SA-ZariyahNeural"},
        "French":  {"male": "fr-FR-HenriNeural",   "female": "fr-FR-DeniseNeural"},
        "Spanish": {"male": "es-ES-AlvaroNeural",  "female": "es-ES-ElviraNeural"},
        "German":  {"male": "de-DE-ConradNeural",  "female": "de-DE-KatjaNeural"},
    }

    # gTTS language codes
    GTTS_LANG = {
        "English": "en", "Urdu": "ur", "Arabic": "ar",
        "French": "fr",  "Spanish": "es", "German": "de",
    }

    # Emotion → (rate, pitch) adjustments for expressiveness
    EMOTION_PROSODY = {
        "angry":       ("+12%", "+20Hz"),
        "furious":     ("+15%", "+25Hz"),
        "happy":       ("+8%",  "+12Hz"),
        "excited":     ("+10%", "+15Hz"),
        "joyful":      ("+8%",  "+10Hz"),
        "sad":         ("-12%", "-12Hz"),
        "melancholy":  ("-10%", "-10Hz"),
        "scared":      ("+12%", "+8Hz"),
        "nervous":     ("+10%", "+5Hz"),
        "whispering":  ("-20%", "-8Hz"),
        "determined":  ("+5%",  "+5Hz"),
        "confused":    ("-5%",  "+3Hz"),
        "surprised":   ("+5%",  "+18Hz"),
        "neutral":     ("+0%",  "+0Hz"),
    }

    def execute(
        self,
        text: str,
        character_name: str,
        voice_personality: str,
        emotion: str,
        output_dir: str = "assets/audio/dialogue",
        provider: int = 4,
        language: str = "English",
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)

        import hashlib
        filename_hash = hashlib.md5(f"{character_name}_{emotion}_{text}_{voice_personality}".encode()).hexdigest()[:8]
        ext = ".mp3" if provider in [3, 4] else ".wav"
        output_path = os.path.join(output_dir, f"{character_name.lower()}_{emotion.lower()}_{filename_hash}{ext}")

        if os.path.exists(output_path):
            print(f"[TTS] Cached: {output_path}")
            return output_path

        if provider == 1:
            return self._generate_coqui(text, character_name, emotion, output_path)
        elif provider == 2:
            return self._generate_elevenlabs(text, voice_personality, emotion, output_path)
        elif provider == 3:
            return self._generate_gtts(text, output_path, language)
        elif provider == 4:
            return self._generate_edge_tts(text, character_name, voice_personality, emotion, output_path, language)
        else:
            raise ValueError("Invalid provider. Use 1 (Coqui), 2 (ElevenLabs), 3 (gTTS), or 4 (Edge-TTS).")

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _generate_coqui(self, text: str, character_name: str, emotion: str, output_path: str) -> str:
        try:
            from TTS.api import TTS
        except ImportError:
            raise ImportError("Install TTS: pip install TTS (requires Python <3.12)")
        print(f"[Coqui TTS] Generating for {character_name} ({emotion})...")
        tts = TTS(model_name="tts_models/en/ljspeech/fast_pitch")
        tts.tts_to_file(text=text, file_path=output_path)
        return output_path

    def _generate_elevenlabs(self, text: str, voice_personality: str, emotion: str, output_path: str) -> str:
        try:
            from elevenlabs.client import ElevenLabs
        except ImportError:
            raise ImportError("Install elevenlabs: pip install elevenlabs")
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY not set in .env")
        client = ElevenLabs(api_key=api_key)
        voice_id = voice_personality if voice_personality else "21m00Tcm4TlvDq8ikWAM"
        print(f"[ElevenLabs] Generating (voice: {voice_id}, emotion: {emotion})...")
        audio_iterator = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        with open(output_path, "wb") as f:
            for chunk in audio_iterator:
                f.write(chunk)
        return output_path

    def _generate_gtts(self, text: str, output_path: str, language: str = "English") -> str:
        try:
            from gtts import gTTS
        except ImportError:
            raise ImportError("Install gTTS: pip install gTTS")
        lang_code = self.GTTS_LANG.get(language, "en")
        gTTS(text=text, lang=lang_code, slow=False).save(output_path)
        print(f"[gTTS] Saved: {output_path} (lang={lang_code})")
        return output_path

    def _generate_edge_tts(
        self, text: str, character_name: str, voice_personality: str, emotion: str, output_path: str,
        language: str = "English",
    ) -> str:
        try:
            import edge_tts
        except ImportError:
            raise ImportError("Install edge-tts: pip install edge-tts")

        voice = self._map_edge_voice(voice_personality, language)
        rate, pitch = self.EMOTION_PROSODY.get(emotion.lower(), ("+0%", "+0Hz"))

        print(f"[Edge-TTS] {character_name} | voice={voice} | emotion={emotion} | rate={rate} pitch={pitch}")

        async def _generate(r, p):
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=r, pitch=p)
            await communicate.save(output_path)

        try:
            self._run_async(_generate(rate, pitch))
        except Exception as e:
            # Some voices (especially non-English) reject SSML prosody — retry flat
            if "+0%" not in rate or "+0Hz" not in pitch:
                print(f"[Edge-TTS] Prosody failed ({e}), retrying without rate/pitch…")
                if os.path.exists(output_path):
                    os.remove(output_path)
                self._run_async(_generate("+0%", "+0Hz"))
            else:
                raise

        print(f"[Edge-TTS] Saved: {output_path}")
        return output_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _run_async(self, coro):
        """Safely run an async coroutine from sync code."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, coro).result()
            else:
                loop.run_until_complete(coro)
        except RuntimeError:
            asyncio.run(coro)

    def _map_edge_voice(self, voice_personality: str, language: str = "English") -> str:
        """Maps character voice_personality to a Microsoft Edge neural voice.
        Non-English languages use a single male/female pair; English gets the full variety.
        """
        p = voice_personality.lower() if voice_personality else ""
        is_female = any(w in p for w in ("female", "woman", "girl", "lady"))
        is_male = not is_female and any(w in p for w in ("male", "man", "boy", "guy"))

        # Non-English: pick male or female voice for that locale
        if language != "English" and language in self.LANG_VOICES:
            lang_pair = self.LANG_VOICES[language]
            return lang_pair["female"] if is_female else lang_pair["male"]

        # English — full variety based on personality keywords
        if "deep" in p or "authoritative" in p or "booming" in p:
            return self.EDGE_VOICES["male_deep"]
        if "british" in p or "english accent" in p or "uk" in p:
            return self.EDGE_VOICES["male_british"] if not is_female else self.EDGE_VOICES["female_british"]
        if "smooth" in p or "confident" in p or "arrogant" in p:
            return self.EDGE_VOICES["male_confident"]
        if "old" in p or "elderly" in p or "wise" in p or "aged" in p:
            return self.EDGE_VOICES["male_old"]
        if "young" in p or "teen" in p or "child" in p or "innocent" in p:
            return self.EDGE_VOICES["female_young"] if is_female else self.EDGE_VOICES["male_young"]
        if "energetic" in p or "fierce" in p or "strong" in p or "bold" in p:
            return self.EDGE_VOICES["female_energetic"] if is_female else self.EDGE_VOICES["male_energetic"]
        if "warm" in p or "gentle" in p or "soft" in p or "kind" in p:
            return self.EDGE_VOICES["female_warm"] if not is_male else self.EDGE_VOICES["male_old"]
        if "professional" in p or "formal" in p or "crisp" in p:
            return self.EDGE_VOICES["female_professional"] if is_female else self.EDGE_VOICES["male_narrator"]
        if "mature" in p or "experienced" in p:
            return self.EDGE_VOICES["female_mature"] if is_female else self.EDGE_VOICES["male_old"]
        if "narrator" in p or "storyteller" in p:
            return self.EDGE_VOICES["male_narrator"]

        if is_female:
            return self.EDGE_VOICES["female_warm"]
        if is_male:
            return self.EDGE_VOICES["male_deep"]
        return self.EDGE_VOICES["male_narrator"]

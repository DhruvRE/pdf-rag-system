"""
Hybrid AI & Rule-Based Question Structurer & Normalizer.
Combines high-speed layout rules with Local (Ollama) or Cloud (Google Gemini / Mistral) LLMs
to produce 100% clean, noise-free, LaTeX-formatted question objects.
"""

import urllib.request
import json
import re

from src.config import (
    LLM_PROVIDER,
    CLOUD_PROVIDER,
    OLLAMA_API_URL,
    OLLAMA_MODEL_NAME,
    OLLAMA_API_KEY,
    GOOGLE_API_KEY,
    GEMINI_MODEL_NAME,
    MISTRAL_API_KEY,
    MISTRAL_MODEL_NAME
)

MODEL_NAME = OLLAMA_MODEL_NAME


def normalize_latex_rules(text: str) -> str:
    """Fast deterministic rule-based LaTeX & chemical formula normalizer."""
    if not text:
        return ""
    t = text
    # Delta & radicals
    t = t.replace("∆", r"$\Delta$")
    t = re.sub(r"√\s*(\d+|\w+)", lambda m: f"$\\sqrt{{{m.group(1)}}}$", t)
    
    # Exponents & units
    t = re.sub(r"\b10\-(\d+)", r"$10^{-\1}$", t)
    t = re.sub(r"\b10(\d{2,})\b", r"$10^{\1}$", t)
    t = re.sub(r"\b([a-zA-Z]+)\-(\d+)\b", lambda m: f"$\\text{{{m.group(1)}}}^{{-{m.group(2)}}}$", t)
    t = re.sub(r"\b([A-Za-z]+)\s*(\d+[\+\-])\b", lambda m: f"$\\text{{{m.group(1)}}}^{{{m.group(2)}}}$", t)
    
    # Orbital terms
    t = re.sub(r"\bt2g\b", r"$t_{2g}$", t)
    t = re.sub(r"\beg\b", r"$e_g$", t)
    
    # Greek & Angles
    t = t.replace("𝛱", r"$\pi$").replace("π", r"$\pi$")
    t = t.replace("θ", r"$\theta$").replace("𝜃", r"$\theta$")
    t = re.sub(r"(\d+)\s*(?:°|deg|\^o)", lambda m: f"${m.group(1)}^\\circ$", t)
    
    # Trig functions
    t = re.sub(r"\b(sin|cos|tan|cot|sec|cosec)\b\s*([A-Za-z0-9θ𝜃$\\]+)", lambda m: f"$\\text{{{m.group(1)}}}({m.group(2)})$", t)
    
    return t


def _call_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
    
    req = urllib.request.Request(OLLAMA_API_URL, data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        return data.get("response", "")


def _call_google_gemini(prompt: str) -> str:
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable is not set")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                return parts[0].get("text", "")
    return ""


def _call_mistral(prompt: str) -> str:
    if not MISTRAL_API_KEY:
        raise ValueError("MISTRAL_API_KEY environment variable is not set")
    
    url = "https://api.mistral.ai/v1/chat/completions"
    payload = json.dumps({
        "model": MISTRAL_MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }).encode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    req = urllib.request.Request(url, data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        choices = data.get("choices", [])
        if choices and "message" in choices[0]:
            return choices[0]["message"].get("content", "")
    return ""


def enhance_question_with_ai(raw_text: str, question_num: str = "", use_ollama: bool = False, provider: str = None) -> dict:
    """
    Normalizes raw question text into structured JSON.
    Supports Local (Ollama) or Cloud (Google Gemini / Mistral) LLMs based on configuration or provider override.
    """
    clean_text = normalize_latex_rules(raw_text)

    active_provider = provider if provider else LLM_PROVIDER

    if use_ollama:
        try:
            prompt = f"Format this question as JSON with keys stem_latex, options, subparts. Input:\n{raw_text}"
            res_text = ""

            if active_provider == "cloud":
                if CLOUD_PROVIDER == "mistral":
                    res_text = _call_mistral(prompt)
                else:
                    res_text = _call_google_gemini(prompt)
            else:
                res_text = _call_ollama(prompt)

            m = re.search(r"\{.*\}", res_text, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception:
            pass

    return {
        "question_number": question_num,
        "clean_full_text": clean_text,
        "latex_stem": clean_text
    }

"""
AI service via OpenRouter.
Full multilingual: English, Hindi, Tamil, Telugu.
Wellness links (yoga, mudra, music) are always appended by code — never by AI.
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import GrokAPIError

logger = logging.getLogger(__name__)

# AI only generates the empathy + food + quick tip text.
# Yoga/mudra/music links are appended by our code — not left to the AI.
SYSTEM_PROMPT = """You are Sakhi, a menstrual health assistant. Be brief and warm.

IF user expresses any mood/pain/emotion, reply EXACTLY in this format (nothing else):
💭 [1 empathetic sentence]

🥗 *Food:* food1 • food2 • food3
💡 [1 quick practical tip]
⚠️ _Consult a doctor if severe._

FOR all other health questions:
[2-3 sentences max]
⚠️ _Consult a doctor if needed._

STRICT: Max 60 words. No extra sections. No yoga links. No mudra links. Match user language exactly."""


# ---------------------------------------------------------------------------
# Mood keyword detection
# ---------------------------------------------------------------------------
MOOD_KEYWORDS = {
    "en": [
        "sad", "angry", "irritable", "tired", "exhausted", "stressed", "anxious",
        "depressed", "overwhelmed", "moody", "low", "upset", "crying", "emotional",
        "bloated", "crampy", "cramps", "pain", "nauseous", "dizzy", "headache",
        "fatigue", "mood swing", "not feeling well", "feeling bad", "feeling down",
        "cant sleep", "can't sleep", "no energy", "restless", "heavy", "worried",
        "scared", "lonely", "hopeless", "panic", "irritated", "uncomfortable",
    ],
    "hi": [
        "उदास", "थकान", "दर्द", "चिड़चिड़ा", "तनाव", "घबराहट", "रो",
        "नींद", "थका", "सिरदर्द", "मतली", "भारी", "परेशान", "बेचैन",
        "अकेला", "डर", "गुस्सा", "कमज़ोर", "थकी", "पेट दर्द", "ऐंठन",
    ],
    "ta": [
        "சோர்வு", "வலி", "கோபம்", "மன அழுத்தம்", "தலைவலி", "குமட்டல்",
        "தூக்கமின்மை", "அழுகை", "கவலை", "சோகம்", "பயம்", "தனிமை",
        "வயிற்று வலி", "சோர்ந்து", "படபடப்பு", "வலிக்கிறது",
    ],
    "te": [
        "విచారం", "అలసట", "నొప్పి", "కోపం", "ఒత్తిడి", "ఆందోళన",
        "తలనొప్పి", "వికారం", "నిద్రలేమి", "భారంగా", "అలసిన",
        "బాధగా", "నీరసం", "కడుపునొప్పి", "ఏడుపు", "భయం",
        "ఒంటరిగా", "కంగారు", "చికాకు", "నీరసంగా", "కడుపు నొప్పి",
        "నొప్పిగా", "నొప్పి వస్తోంది", "నొప్పి ఉంది", "నొప్పి తగ్గడం",
        "బాధ", "వేదన", "క్రాంప్స్", "నొప్పులు",
    ],
}


def detect_mood(text: str, language: str = "en") -> bool:
    """Return True if any mood/pain keyword found in text."""
    text_lower = text.lower()
    # Check language-specific + English keywords
    lang_keywords = MOOD_KEYWORDS.get(language, [])
    en_keywords = MOOD_KEYWORDS["en"]
    all_keywords = lang_keywords + en_keywords
    return any(k in text_lower for k in all_keywords)


def classify_mood(text: str) -> str:
    """Map message to mood category for targeted recommendations."""
    t = text.lower()
    if any(w in t for w in ["pain", "cramp", "నొప్పి", "కడుపు నొప్పి", "కడుపునొప్పి", "నొప్పులు", "నొప్పిగా", "क्रैम्प", "पेट दर्द", "வலி", "வயிற்று வலி"]):
        return "pain"
    if any(w in t for w in ["stress", "anxious", "panic", "worried", "ఒత్తిడి", "ఆందోళన", "కంగారు", "तनाव", "घबराहट", "மன அழுத்தம்", "படபடப்பு"]):
        return "stress"
    if any(w in t for w in ["sad", "cry", "depress", "lonely", "hopeless", "విచారం", "ఏడుపు", "ఒంటరిగా", "బాధ", "वेदना", "उदास", "अकेला", "சோகம்", "அழுகை", "தனிமை"]):
        return "sadness"
    if any(w in t for w in ["tired", "exhaust", "fatigue", "no energy", "అలసట", "నీరసం", "నీరసంగా", "थकान", "थका", "சோர்வு", "சோர்ந்து"]):
        return "fatigue"
    if any(w in t for w in ["angry", "irritab", "కోపం", "చికాకు", "गुस्सा", "चिड़चिड़ा", "கோபம்"]):
        return "anger"
    if any(w in t for w in ["sleep", "నిద్రలేమి", "నిద్ర", "नींद", "தூக்கமின்மை"]):
        return "insomnia"
    return "general"


# ---------------------------------------------------------------------------
# Yoga poses — per mood per language
# ---------------------------------------------------------------------------
YOGA_BY_MOOD: dict[str, dict[str, list[tuple]]] = {
    "pain": {
        "en": [("Child's Pose", "https://www.youtube.com/results?search_query=balasana+period+cramp+relief"), ("Supine Twist", "https://www.youtube.com/results?search_query=supine+twist+period+pain"), ("Cat-Cow", "https://www.youtube.com/results?search_query=cat+cow+stretch+menstrual+pain")],
        "hi": [("बालासन", "https://www.youtube.com/results?search_query=balasana+period+cramp+relief"), ("सुप्त मत्स्येन्द्रासन", "https://www.youtube.com/results?search_query=supine+twist+period+pain"), ("मार्जरी आसन", "https://www.youtube.com/results?search_query=cat+cow+stretch+menstrual+pain")],
        "ta": [("குழந்தை தோரணை", "https://www.youtube.com/results?search_query=balasana+period+cramp+relief"), ("சுப்த முறுக்கு", "https://www.youtube.com/results?search_query=supine+twist+period+pain"), ("பூனை-பசு நீட்சி", "https://www.youtube.com/results?search_query=cat+cow+stretch+menstrual+pain")],
        "te": [("బాలాసన", "https://www.youtube.com/results?search_query=balasana+period+cramp+relief"), ("సుప్త మత్స్యేంద్రాసన", "https://www.youtube.com/results?search_query=supine+twist+period+pain"), ("మార్జరాసన", "https://www.youtube.com/results?search_query=cat+cow+stretch+menstrual+pain")],
    },
    "stress": {
        "en": [("Child's Pose", "https://www.youtube.com/results?search_query=childs+pose+stress+relief"), ("Legs Up Wall", "https://www.youtube.com/results?search_query=viparita+karani+anxiety+relief"), ("Forward Fold", "https://www.youtube.com/results?search_query=standing+forward+fold+stress")],
        "hi": [("बालासन", "https://www.youtube.com/results?search_query=childs+pose+stress+relief"), ("विपरीत करणी", "https://www.youtube.com/results?search_query=viparita+karani+anxiety+relief"), ("उत्तानासन", "https://www.youtube.com/results?search_query=standing+forward+fold+stress")],
        "ta": [("குழந்தை தோரணை", "https://www.youtube.com/results?search_query=childs+pose+stress+relief"), ("கால்கள் மேலே சுவர்", "https://www.youtube.com/results?search_query=viparita+karani+anxiety+relief"), ("முன்னோக்கி மடக்கு", "https://www.youtube.com/results?search_query=standing+forward+fold+stress")],
        "te": [("బాలాసన", "https://www.youtube.com/results?search_query=childs+pose+stress+relief"), ("విపరీత కరణి", "https://www.youtube.com/results?search_query=viparita+karani+anxiety+relief"), ("ఉత్తానాసన", "https://www.youtube.com/results?search_query=standing+forward+fold+stress")],
    },
    "sadness": {
        "en": [("Heart Opener", "https://www.youtube.com/results?search_query=heart+opening+yoga+sadness"), ("Butterfly Pose", "https://www.youtube.com/results?search_query=baddha+konasana+mood+lift"), ("Sun Salutation", "https://www.youtube.com/results?search_query=surya+namaskar+depression+yoga")],
        "hi": [("हृदय खोलने वाला आसन", "https://www.youtube.com/results?search_query=heart+opening+yoga+sadness"), ("बद्धकोणासन", "https://www.youtube.com/results?search_query=baddha+konasana+mood+lift"), ("सूर्य नमस्कार", "https://www.youtube.com/results?search_query=surya+namaskar+depression+yoga")],
        "ta": [("இதய திறப்பு", "https://www.youtube.com/results?search_query=heart+opening+yoga+sadness"), ("பட்டாம்பூச்சி தோரணை", "https://www.youtube.com/results?search_query=baddha+konasana+mood+lift"), ("சூர்ய நமஸ்காரம்", "https://www.youtube.com/results?search_query=surya+namaskar+depression+yoga")],
        "te": [("హృదయ విచ్చుకొలుపు", "https://www.youtube.com/results?search_query=heart+opening+yoga+sadness"), ("బద్ధ కోణాసన", "https://www.youtube.com/results?search_query=baddha+konasana+mood+lift"), ("సూర్య నమస్కారం", "https://www.youtube.com/results?search_query=surya+namaskar+depression+yoga")],
    },
    "fatigue": {
        "en": [("Legs Up Wall", "https://www.youtube.com/results?search_query=viparita+karani+fatigue+energy"), ("Corpse Pose", "https://www.youtube.com/results?search_query=savasana+restore+energy"), ("Restorative Yoga", "https://www.youtube.com/results?search_query=restorative+yoga+tiredness")],
        "hi": [("विपरीत करणी", "https://www.youtube.com/results?search_query=viparita+karani+fatigue+energy"), ("शवासन", "https://www.youtube.com/results?search_query=savasana+restore+energy"), ("पुनर्स्थापना योग", "https://www.youtube.com/results?search_query=restorative+yoga+tiredness")],
        "ta": [("கால்கள் மேலே சுவர்", "https://www.youtube.com/results?search_query=viparita+karani+fatigue+energy"), ("சவாசனம்", "https://www.youtube.com/results?search_query=savasana+restore+energy"), ("மீட்சி யோகா", "https://www.youtube.com/results?search_query=restorative+yoga+tiredness")],
        "te": [("విపరీత కరణి", "https://www.youtube.com/results?search_query=viparita+karani+fatigue+energy"), ("శవాసన", "https://www.youtube.com/results?search_query=savasana+restore+energy"), ("రిస్టోరేటివ్ యోగా", "https://www.youtube.com/results?search_query=restorative+yoga+tiredness")],
    },
    "anger": {
        "en": [("Lion's Breath", "https://www.youtube.com/results?search_query=lion+breath+pranayama+anger"), ("Seated Twist", "https://www.youtube.com/results?search_query=seated+spinal+twist+anger+release"), ("Child's Pose", "https://www.youtube.com/results?search_query=childs+pose+calm+anger")],
        "hi": [("सिंह प्राणायाम", "https://www.youtube.com/results?search_query=lion+breath+pranayama+anger"), ("बैठकर मेरुदंड मोड़", "https://www.youtube.com/results?search_query=seated+spinal+twist+anger+release"), ("बालासन", "https://www.youtube.com/results?search_query=childs+pose+calm+anger")],
        "ta": [("சிங்க மூச்சு", "https://www.youtube.com/results?search_query=lion+breath+pranayama+anger"), ("இருக்கை முறுக்கு", "https://www.youtube.com/results?search_query=seated+spinal+twist+anger+release"), ("குழந்தை தோரணை", "https://www.youtube.com/results?search_query=childs+pose+calm+anger")],
        "te": [("సింహ ప్రాణాయామ", "https://www.youtube.com/results?search_query=lion+breath+pranayama+anger"), ("కూర్చున్న వెన్నెముక మెలిక", "https://www.youtube.com/results?search_query=seated+spinal+twist+anger+release"), ("బాలాసన", "https://www.youtube.com/results?search_query=childs+pose+calm+anger")],
    },
    "insomnia": {
        "en": [("Legs Up Wall", "https://www.youtube.com/results?search_query=yoga+for+sleep+legs+up+wall"), ("Yoga Nidra", "https://www.youtube.com/results?search_query=yoga+nidra+insomnia+sleep"), ("Forward Fold", "https://www.youtube.com/results?search_query=forward+fold+bedtime+yoga")],
        "hi": [("विपरीत करणी", "https://www.youtube.com/results?search_query=yoga+for+sleep+legs+up+wall"), ("योग निद्रा", "https://www.youtube.com/results?search_query=yoga+nidra+insomnia+sleep"), ("उत्तानासन", "https://www.youtube.com/results?search_query=forward+fold+bedtime+yoga")],
        "ta": [("கால்கள் மேலே", "https://www.youtube.com/results?search_query=yoga+for+sleep+legs+up+wall"), ("யோக நித்திரை", "https://www.youtube.com/results?search_query=yoga+nidra+insomnia+sleep"), ("முன்னோக்கி மடக்கு", "https://www.youtube.com/results?search_query=forward+fold+bedtime+yoga")],
        "te": [("విపరీత కరణి", "https://www.youtube.com/results?search_query=yoga+for+sleep+legs+up+wall"), ("యోగ నిద్ర", "https://www.youtube.com/results?search_query=yoga+nidra+insomnia+sleep"), ("ఉత్తానాసన", "https://www.youtube.com/results?search_query=forward+fold+bedtime+yoga")],
    },
    "general": {
        "en": [("Child's Pose", "https://www.youtube.com/results?search_query=balasana+period+pain"), ("Legs Up Wall", "https://www.youtube.com/results?search_query=viparita+karani+menstrual"), ("Cat-Cow", "https://www.youtube.com/results?search_query=cat+cow+stretch+period")],
        "hi": [("बालासन", "https://www.youtube.com/results?search_query=balasana+period+pain"), ("विपरीत करणी", "https://www.youtube.com/results?search_query=viparita+karani+menstrual"), ("मार्जरी आसन", "https://www.youtube.com/results?search_query=cat+cow+stretch+period")],
        "ta": [("குழந்தை தோரணை", "https://www.youtube.com/results?search_query=balasana+period+pain"), ("கால்கள் மேலே சுவர்", "https://www.youtube.com/results?search_query=viparita+karani+menstrual"), ("பூனை-பசு", "https://www.youtube.com/results?search_query=cat+cow+stretch+period")],
        "te": [("బాలాసన", "https://www.youtube.com/results?search_query=balasana+period+pain"), ("విపరీత కరణి", "https://www.youtube.com/results?search_query=viparita+karani+menstrual"), ("మార్జరాసన", "https://www.youtube.com/results?search_query=cat+cow+stretch+period")],
    },
}

# ---------------------------------------------------------------------------
# Mudras — per mood per language
# ---------------------------------------------------------------------------
MUDRAS_BY_MOOD: dict[str, dict[str, list[tuple]]] = {
    "pain":     {"en": [("Apana Mudra 🤲", "https://www.youtube.com/results?search_query=apana+mudra+menstrual+pain"), ("Shakti Mudra 🤲", "https://www.youtube.com/results?search_query=shakti+mudra+period+cramps")], "hi": [("अपान मुद्रा 🤲", "https://www.youtube.com/results?search_query=apana+mudra+menstrual+pain"), ("शक्ति मुद्रा 🤲", "https://www.youtube.com/results?search_query=shakti+mudra+period+cramps")], "ta": [("அபான முத்திரை 🤲", "https://www.youtube.com/results?search_query=apana+mudra+menstrual+pain"), ("சக்தி முத்திரை 🤲", "https://www.youtube.com/results?search_query=shakti+mudra+period+cramps")], "te": [("అపాన ముద్ర 🤲", "https://www.youtube.com/results?search_query=apana+mudra+menstrual+pain"), ("శక్తి ముద్ర 🤲", "https://www.youtube.com/results?search_query=shakti+mudra+period+cramps")]},
    "stress":   {"en": [("Gyan Mudra 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+stress+anxiety+relief"), ("Prana Mudra 🤲", "https://www.youtube.com/results?search_query=prana+mudra+calm+stress")], "hi": [("ज्ञान मुद्रा 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+stress+anxiety+relief"), ("प्राण मुद्रा 🤲", "https://www.youtube.com/results?search_query=prana+mudra+calm+stress")], "ta": [("ஞான முத்திரை 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+stress+anxiety+relief"), ("பிராண முத்திரை 🤲", "https://www.youtube.com/results?search_query=prana+mudra+calm+stress")], "te": [("జ్ఞాన ముద్ర 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+stress+anxiety+relief"), ("ప్రాణ ముద్ర 🤲", "https://www.youtube.com/results?search_query=prana+mudra+calm+stress")]},
    "sadness":  {"en": [("Ahamkara Mudra 🤲", "https://www.youtube.com/results?search_query=ahamkara+mudra+confidence+sadness"), ("Surya Mudra 🤲", "https://www.youtube.com/results?search_query=surya+mudra+energy+mood")], "hi": [("अहंकार मुद्रा 🤲", "https://www.youtube.com/results?search_query=ahamkara+mudra+confidence+sadness"), ("सूर्य मुद्रा 🤲", "https://www.youtube.com/results?search_query=surya+mudra+energy+mood")], "ta": [("அகங்கார முத்திரை 🤲", "https://www.youtube.com/results?search_query=ahamkara+mudra+confidence+sadness"), ("சூர்ய முத்திரை 🤲", "https://www.youtube.com/results?search_query=surya+mudra+energy+mood")], "te": [("అహంకార ముద్ర 🤲", "https://www.youtube.com/results?search_query=ahamkara+mudra+confidence+sadness"), ("సూర్య ముద్ర 🤲", "https://www.youtube.com/results?search_query=surya+mudra+energy+mood")]},
    "fatigue":  {"en": [("Prana Mudra 🤲", "https://www.youtube.com/results?search_query=prana+mudra+energy+fatigue"), ("Surya Mudra 🤲", "https://www.youtube.com/results?search_query=surya+mudra+vitality+tiredness")], "hi": [("प्राण मुद्रा 🤲", "https://www.youtube.com/results?search_query=prana+mudra+energy+fatigue"), ("सूर्य मुद्रा 🤲", "https://www.youtube.com/results?search_query=surya+mudra+vitality+tiredness")], "ta": [("பிராண முத்திரை 🤲", "https://www.youtube.com/results?search_query=prana+mudra+energy+fatigue"), ("சூர்ய முத்திரை 🤲", "https://www.youtube.com/results?search_query=surya+mudra+vitality+tiredness")], "te": [("ప్రాణ ముద్ర 🤲", "https://www.youtube.com/results?search_query=prana+mudra+energy+fatigue"), ("సూర్య ముద్ర 🤲", "https://www.youtube.com/results?search_query=surya+mudra+vitality+tiredness")]},
    "anger":    {"en": [("Shunya Mudra 🤲", "https://www.youtube.com/results?search_query=shunya+mudra+anger+calm"), ("Vayu Mudra 🤲", "https://www.youtube.com/results?search_query=vayu+mudra+anger+relief")], "hi": [("शून्य मुद्रा 🤲", "https://www.youtube.com/results?search_query=shunya+mudra+anger+calm"), ("वायु मुद्रा 🤲", "https://www.youtube.com/results?search_query=vayu+mudra+anger+relief")], "ta": [("சூன்ய முத்திரை 🤲", "https://www.youtube.com/results?search_query=shunya+mudra+anger+calm"), ("வாயு முத்திரை 🤲", "https://www.youtube.com/results?search_query=vayu+mudra+anger+relief")], "te": [("శూన్య ముద్ర 🤲", "https://www.youtube.com/results?search_query=shunya+mudra+anger+calm"), ("వాయు ముద్ర 🤲", "https://www.youtube.com/results?search_query=vayu+mudra+anger+relief")]},
    "insomnia": {"en": [("Gyan Mudra 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+sleep+insomnia"), ("Yoni Mudra 🤲", "https://www.youtube.com/results?search_query=yoni+mudra+deep+sleep")], "hi": [("ज्ञान मुद्रा 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+sleep+insomnia"), ("योनि मुद्रा 🤲", "https://www.youtube.com/results?search_query=yoni+mudra+deep+sleep")], "ta": [("ஞான முத்திரை 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+sleep+insomnia"), ("யோனி முத்திரை 🤲", "https://www.youtube.com/results?search_query=yoni+mudra+deep+sleep")], "te": [("జ్ఞాన ముద్ర 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+sleep+insomnia"), ("యోని ముద్ర 🤲", "https://www.youtube.com/results?search_query=yoni+mudra+deep+sleep")]},
    "general":  {"en": [("Gyan Mudra 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+menstrual+health"), ("Apana Mudra 🤲", "https://www.youtube.com/results?search_query=apana+mudra+women+health")], "hi": [("ज्ञान मुद्रा 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+menstrual+health"), ("अपान मुद्रा 🤲", "https://www.youtube.com/results?search_query=apana+mudra+women+health")], "ta": [("ஞான முத்திரை 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+menstrual+health"), ("அபான முத்திரை 🤲", "https://www.youtube.com/results?search_query=apana+mudra+women+health")], "te": [("జ్ఞాన ముద్ర 🤲", "https://www.youtube.com/results?search_query=gyan+mudra+menstrual+health"), ("అపాన ముద్ర 🤲", "https://www.youtube.com/results?search_query=apana+mudra+women+health")]},
}

# ---------------------------------------------------------------------------
# Healing frequency music — per mood per language
# ---------------------------------------------------------------------------
MUSIC_BY_MOOD: dict[str, dict[str, tuple]] = {
    "pain":     {"en": ("174 Hz – Pain Relief 🎵", "https://www.youtube.com/results?search_query=174hz+pain+relief+solfeggio"), "hi": ("174 Hz – दर्द निवारण 🎵", "https://www.youtube.com/results?search_query=174hz+pain+relief+solfeggio"), "ta": ("174 Hz – வலி நிவாரணம் 🎵", "https://www.youtube.com/results?search_query=174hz+pain+relief+solfeggio"), "te": ("174 Hz – నొప్పి నివారణ 🎵", "https://www.youtube.com/results?search_query=174hz+pain+relief+solfeggio")},
    "stress":   {"en": ("432 Hz – Deep Calm 🎵", "https://www.youtube.com/results?search_query=432hz+stress+relief+calm+music"), "hi": ("432 Hz – गहरी शांति 🎵", "https://www.youtube.com/results?search_query=432hz+stress+relief+calm+music"), "ta": ("432 Hz – ஆழ்ந்த அமைதி 🎵", "https://www.youtube.com/results?search_query=432hz+stress+relief+calm+music"), "te": ("432 Hz – లోతైన శాంతి 🎵", "https://www.youtube.com/results?search_query=432hz+stress+relief+calm+music")},
    "sadness":  {"en": ("528 Hz – Heart Heal 🎵", "https://www.youtube.com/results?search_query=528hz+emotional+healing+music"), "hi": ("528 Hz – हृदय उपचार 🎵", "https://www.youtube.com/results?search_query=528hz+emotional+healing+music"), "ta": ("528 Hz – இதய குணமாக்கல் 🎵", "https://www.youtube.com/results?search_query=528hz+emotional+healing+music"), "te": ("528 Hz – హృదయ నయం 🎵", "https://www.youtube.com/results?search_query=528hz+emotional+healing+music")},
    "fatigue":  {"en": ("285 Hz – Energy Boost 🎵", "https://www.youtube.com/results?search_query=285hz+energy+healing+frequency"), "hi": ("285 Hz – ऊर्जा बढ़ाएं 🎵", "https://www.youtube.com/results?search_query=285hz+energy+healing+frequency"), "ta": ("285 Hz – ஆற்றல் அதிகரிப்பு 🎵", "https://www.youtube.com/results?search_query=285hz+energy+healing+frequency"), "te": ("285 Hz – శక్తి పెంపు 🎵", "https://www.youtube.com/results?search_query=285hz+energy+healing+frequency")},
    "anger":    {"en": ("396 Hz – Release Anger 🎵", "https://www.youtube.com/results?search_query=396hz+release+anger+solfeggio"), "hi": ("396 Hz – क्रोध मुक्ति 🎵", "https://www.youtube.com/results?search_query=396hz+release+anger+solfeggio"), "ta": ("396 Hz – கோபம் விடுதலை 🎵", "https://www.youtube.com/results?search_query=396hz+release+anger+solfeggio"), "te": ("396 Hz – కోపం విముక్తి 🎵", "https://www.youtube.com/results?search_query=396hz+release+anger+solfeggio")},
    "insomnia": {"en": ("Delta Waves – Deep Sleep 🎵", "https://www.youtube.com/results?search_query=delta+waves+deep+sleep+music"), "hi": ("डेल्टा वेव्स – गहरी नींद 🎵", "https://www.youtube.com/results?search_query=delta+waves+deep+sleep+music"), "ta": ("டெல்டா அலைகள் – ஆழ்ந்த தூக்கம் 🎵", "https://www.youtube.com/results?search_query=delta+waves+deep+sleep+music"), "te": ("డెల్టా వేవ్స్ – గాఢ నిద్ర 🎵", "https://www.youtube.com/results?search_query=delta+waves+deep+sleep+music")},
    "general":  {"en": ("432 Hz – Balance & Heal 🎵", "https://www.youtube.com/results?search_query=432hz+menstrual+cycle+healing"), "hi": ("432 Hz – संतुलन और उपचार 🎵", "https://www.youtube.com/results?search_query=432hz+menstrual+cycle+healing"), "ta": ("432 Hz – சமநிலை & குணமாக்கல் 🎵", "https://www.youtube.com/results?search_query=432hz+menstrual+cycle+healing"), "te": ("432 Hz – సమతుల్యత & నయం 🎵", "https://www.youtube.com/results?search_query=432hz+menstrual+cycle+healing")},
}

SECTION_TITLES = {
    "en": {"yoga": "🧘 *Yoga*",  "mudra": "🤲 *Mudras*",       "music": "🎵 *Healing Music*"},
    "hi": {"yoga": "🧘 *योग*",   "mudra": "🤲 *मुद्राएं*",      "music": "🎵 *उपचार संगीत*"},
    "ta": {"yoga": "🧘 *யோகா*",  "mudra": "🤲 *முத்திரைகள்*",  "music": "🎵 *குணமளிக்கும் இசை*"},
    "te": {"yoga": "🧘 *యోగా*",  "mudra": "🤲 *ముద్రలు*",       "music": "🎵 *హీలింగ్ మ్యూజిక్*"},
}


def build_wellness_links(mood_category: str, language: str = "en") -> str:
    lang = language if language in ("en", "hi", "ta", "te") else "en"
    titles = SECTION_TITLES.get(lang, SECTION_TITLES["en"])
    yoga_poses = YOGA_BY_MOOD.get(mood_category, YOGA_BY_MOOD["general"]).get(lang, YOGA_BY_MOOD["general"]["en"])
    mudras = MUDRAS_BY_MOOD.get(mood_category, MUDRAS_BY_MOOD["general"]).get(lang, MUDRAS_BY_MOOD["general"]["en"])
    music_name, music_url = MUSIC_BY_MOOD.get(mood_category, MUSIC_BY_MOOD["general"]).get(lang, MUSIC_BY_MOOD["general"]["en"])

    lines = []
    lines.append(titles["yoga"])
    for name, url in yoga_poses:
        lines.append(f"• [{name}]({url})")
    lines.append("")
    lines.append(titles["mudra"])
    for name, url in mudras:
        lines.append(f"• [{name}]({url})")
    lines.append("")
    lines.append(titles["music"])
    lines.append(f"• [{music_name}]({music_url})")
    return "\n".join(lines)


async def ask_grok(user_message: str, language: str = "en") -> str:
    lang_instruction = {
        "hi": "Reply in Hindi.",
        "ta": "Reply in Tamil.",
        "te": "Reply in Telugu.",
    }.get(language, "Reply in English.")

    is_mood = detect_mood(user_message, language)
    mood_category = classify_mood(user_message) if is_mood else "general"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{lang_instruction}\n\n{user_message}"},
    ]

    headers = {
        "Authorization": f"Bearer {settings.GROK_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://sakhimodel.onrender.com",
        "X-Title": "Sakhi Health Assistant",
    }

    payload = {
        "model": settings.GROK_MODEL,
        "messages": messages,
        "max_tokens": 150,
        "temperature": 0.5,
    }

    try:
        async with httpx.AsyncClient(
            base_url=settings.GROK_BASE_URL,
            timeout=httpx.Timeout(connect=5.0, read=settings.GROK_TIMEOUT_SECONDS, write=5.0, pool=2.0),
        ) as client:
            response = await client.post("/chat/completions", headers=headers, json=payload)

        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error("OpenRouter non-200", extra={"status": response.status_code, "detail": error_detail})
            raise GrokAPIError(f"OpenRouter returned {response.status_code}: {error_detail}")

        data = response.json()
        content: Optional[str] = (
            data.get("choices", [{}])[0].get("message", {}).get("content")
        )
        if not content:
            raise GrokAPIError("Empty response from OpenRouter")

        # Always append wellness links from our code — never rely on AI for this
        if is_mood:
            wellness = build_wellness_links(mood_category, language)
            content = f"{content.strip()}\n\n{wellness}"

        logger.info("OpenRouter success", extra={
            "tokens": data.get("usage", {}).get("total_tokens"),
            "mood_category": mood_category,
            "language": language,
            "is_mood": is_mood,
        })
        return content.strip()

    except httpx.TimeoutException as exc:
        raise GrokAPIError("OpenRouter timed out") from exc
    except httpx.RequestError as exc:
        raise GrokAPIError("Network error contacting OpenRouter") from exc

"""
Serious symptom detection.
If triggered, Sakhi asks user to share location and finds nearest hospital.
"""

SERIOUS_KEYWORDS = {
    "en": [
        "chest pain", "cant breathe", "can't breathe", "difficulty breathing",
        "unconscious", "fainted", "heavy bleeding", "bleeding won't stop",
        "severe pain", "extreme pain", "unbearable pain", "vomiting blood",
        "blood in urine", "high fever", "fever 3 days", "fever 4 days",
        "suicidal", "want to die", "kill myself",
        "pregnancy", "pregnant", "missed periods", "no period 3 months",
        "severe cramps", "sharp pain", "stabbing pain",
        "swollen", "lump", "discharge", "abnormal discharge",
    ],
    "hi": [
        "छाती में दर्द", "सांस नहीं आ रही", "बेहोश", "बहुत ज़्यादा खून",
        "तेज़ बुखार", "असहनीय दर्द", "उल्टी में खून", "मरना चाहती",
        "गर्भवती", "गर्भावस्था", "बहुत तेज़ दर्द",
    ],
    "ta": [
        "மார்பு வலி", "மூச்சு வரவில்லை", "மயக்கம்", "அதிக இரத்தம்",
        "கடுமையான காய்ச்சல்", "தாங்கமுடியாத வலி", "கர்ப்பம்", "இறக்க வேண்டும்",
    ],
    "te": [
        "ఛాతీ నొప్పి", "ఊపిరి రావడం లేదు", "స్పృహ తప్పింది", "చాలా రక్తస్రావం",
        "తీవ్రమైన జ్వరం", "భరించలేని నొప్పి", "రక్తం వాంతి", "చనిపోవాలని",
        "గర్భం", "గర్భవతి", "చాలా తీవ్రమైన నొప్పి",
        # romanized
        "chest pain", "upa radu", "spruha tappindi", "chalaraktasravam",
        "tivramaina noppi", "chanipovaalani", "garbham", "garbhavati",
        "severe pain", "heavy bleeding", "blood vastundi",
    ],
}

LOCATION_REQUEST = {
    "en": (
        "⚠️ *This sounds serious.* Please consult a doctor immediately.\n\n"
        "📍 *Share your location* and I'll find the nearest government hospital with contact details for you.\n\n"
        "_Tap the 📎 attachment icon → Location → Share My Live Location or Send My Current Location_"
    ),
    "hi": (
        "⚠️ *यह गंभीर लग रहा है।* कृपया तुरंत डॉक्टर से मिलें।\n\n"
        "📍 *अपनी लोकेशन शेयर करें* और मैं आपके नज़दीकी सरकारी अस्पताल ढूंढूंगी।\n\n"
        "_📎 अटैचमेंट → Location → Send My Current Location दबाएं_"
    ),
    "ta": (
        "⚠️ *இது தீவிரமாகத் தெரிகிறது।* உடனடியாக மருத்துவரை சந்தியுங்கள்.\n\n"
        "📍 *உங்கள் இருப்பிடத்தைப் பகிரவும்* — நான் அருகிலுள்ள அரசு மருத்துவமனையைக் கண்டுபிடிக்கிறேன்.\n\n"
        "_📎 இணைப்பு → Location → Send My Current Location அழுத்தவும்_"
    ),
    "te": (
        "⚠️ *ఇది తీవ్రంగా అనిపిస్తోంది.* దయచేసి వెంటనే డాక్టర్‌ని సంప్రదించండి.\n\n"
        "📍 *మీ లొకేషన్ షేర్ చేయండి* — నేను దగ్గరలో ఉన్న ప్రభుత్వ ఆసుపత్రిని కనుగొంటాను.\n\n"
        "_📎 అటాచ్‌మెంట్ → Location → Send My Current Location నొక్కండి_"
    ),
}

SEARCHING_MSG = {
    "en": "🔍 Finding nearest government hospitals for you...",
    "hi": "🔍 आपके लिए नज़दीकी सरकारी अस्पताल खोज रही हूँ...",
    "ta": "🔍 உங்களுக்காக அருகிலுள்ள அரசு மருத்துவமனையைத் தேடுகிறேன்...",
    "te": "🔍 మీకోసం దగ్గరలో ఉన్న ప్రభుత్వ ఆసుపత్రి వెతుకుతున్నాను...",
}


def is_serious_symptom(text: str, language: str = "en") -> bool:
    """Return True if message contains serious medical symptom keywords."""
    t = text.lower()
    lang_kw = SERIOUS_KEYWORDS.get(language, [])
    en_kw = SERIOUS_KEYWORDS["en"]
    return any(k in t for k in lang_kw + en_kw)


def get_location_request(language: str = "en") -> str:
    return LOCATION_REQUEST.get(language, LOCATION_REQUEST["en"])


def get_searching_msg(language: str = "en") -> str:
    return SEARCHING_MSG.get(language, SEARCHING_MSG["en"])

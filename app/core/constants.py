"""
Conversation state machine constants and localised response strings.
"""


class ConversationState:
    """String-based state names stored in MongoDB."""
    NEW = "NEW"
    AWAITING_LANGUAGE = "AWAITING_LANGUAGE"
    AWAITING_LAST_PERIOD = "AWAITING_LAST_PERIOD"
    ACTIVE = "ACTIVE"


SUPPORTED_LANGUAGES: dict[str, str] = {
    "1": "en",
    "2": "hi",
    "3": "ta",
    "4": "te",
    "en": "en",
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "english": "en",
    "hindi": "hi",
    "tamil": "ta",
    "telugu": "te",
}

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "welcome": (
            "🌸 *Namaste! I'm Sakhi*, your personal menstrual health companion.\n\n"
            "I'll help you track your cycle, predict your next period, and answer "
            "health questions with care.\n\n"
            "Please choose your language:\n"
            "1️⃣ English\n2️⃣ हिंदी (Hindi)\n3️⃣ தமிழ் (Tamil)\n4️⃣ తెలుగు (Telugu)"
        ),
        "language_set": "✅ Great! Language set to *English*.",
        "ask_last_period": (
            "📅 To predict your next cycle, please share the *date your last period started*.\n\n"
            "Format: `DD-MM-YYYY` or `DD/MM/YYYY`\n"
            "Example: `15-03-2025`"
        ),
        "invalid_date": (
            "❌ I couldn't understand that date. Please use `DD-MM-YYYY`.\n"
            "Example: `15-03-2025`"
        ),
        "future_date": "❌ The date can't be in the future. Please enter a valid past date.",
        "date_too_old": "❌ That date seems too far back. Please enter a date within the last 6 months.",
        "prediction": (
            "🌸 *Cycle Prediction*\n\n"
            "📌 Last period started: *{last_period}*\n"
            "🔮 Predicted next period: *{next_period}*\n"
            "📆 Days remaining: *{days_remaining} days*\n\n"
            "You can now ask me anything about your health! 💬\n\n"
            "_Disclaimer: This is an estimate based on a {cycle_length}-day cycle. "
            "Consult a healthcare provider for medical advice._"
        ),
        "already_active": "You're all set! Ask me anything about your cycle or health. 💬",
        "reset_info": "Type /start to reset your profile.",
        "disclaimer": (
            "_⚠️ I'm an AI assistant, not a medical professional. "
            "Always consult a qualified doctor for medical decisions._"
        ),
        "ai_error": (
            "I'm having trouble connecting right now. Please try again in a moment. 🙏\n\n"
            "For urgent concerns, please consult a healthcare provider."
        ),
        "db_error": "Something went wrong on my end. Please try again shortly.",
        "language_unknown": (
            "Please reply with a number:\n1️⃣ English\n2️⃣ हिंदी\n3️⃣ தமிழ்\n4️⃣ తెలుగు"
        ),
    },
    "hi": {
        "welcome": (
            "🌸 *नमस्ते! मैं साखी हूँ*, आपकी व्यक्तिगत मासिक स्वास्थ्य सहायक।\n\n"
            "कृपया भाषा चुनें:\n1️⃣ English\n2️⃣ हिंदी\n3️⃣ தமிழ்\n4️⃣ తెలుగు"
        ),
        "language_set": "✅ बढ़िया! भाषा *हिंदी* पर सेट की गई।",
        "ask_last_period": (
            "📅 आपके अगले मासिक चक्र का अनुमान लगाने के लिए, कृपया *अपने पिछले मासिक धर्म की शुरुआत की तारीख* बताएं।\n\n"
            "प्रारूप: `DD-MM-YYYY`\nउदाहरण: `15-03-2025`"
        ),
        "invalid_date": "❌ तारीख समझ नहीं आई। कृपया `DD-MM-YYYY` प्रारूप में दर्ज करें।",
        "future_date": "❌ तारीख भविष्य की नहीं हो सकती।",
        "date_too_old": "❌ कृपया पिछले 6 महीनों की तारीख दर्ज करें।",
        "prediction": (
            "🌸 *चक्र अनुमान*\n\n"
            "📌 पिछला मासिक: *{last_period}*\n"
            "🔮 अनुमानित अगला मासिक: *{next_period}*\n"
            "📆 शेष दिन: *{days_remaining} दिन*\n\n"
            "अब आप मुझसे स्वास्थ्य संबंधी कोई भी प्रश्न पूछ सकती हैं! 💬\n\n"
            "_यह {cycle_length}-दिन के चक्र पर आधारित अनुमान है। चिकित्सीय सलाह के लिए डॉक्टर से मिलें।_"
        ),
        "already_active": "सब तैयार है! कुछ भी पूछें। 💬",
        "reset_info": "प्रोफ़ाइल रीसेट करने के लिए /start टाइप करें।",
        "disclaimer": "_⚠️ मैं एक AI हूँ, डॉक्टर नहीं। चिकित्सीय निर्णयों के लिए हमेशा डॉक्टर से परामर्श लें।_",
        "ai_error": "अभी कनेक्ट करने में समस्या है। थोड़ी देर बाद पुनः प्रयास करें। 🙏",
        "db_error": "कुछ गड़बड़ हो गई। कृपया दोबारा प्रयास करें।",
        "language_unknown": "कृपया संख्या से उत्तर दें:\n1️⃣ English\n2️⃣ हिंदी\n3️⃣ தமிழ்\n4️⃣ తెలుగు",
    },
    "ta": {
        "welcome": (
            "🌸 *வணக்கம்! நான் சகி*, உங்கள் மாதவிடாய் சுகாதார உதவியாளர்.\n\n"
            "மொழியைத் தேர்வு செய்யுங்கள்:\n1️⃣ English\n2️⃣ हिंदी\n3️⃣ தமிழ்\n4️⃣ తెలుగు"
        ),
        "language_set": "✅ சரி! மொழி *தமிழ்* ஆக அமைக்கப்பட்டது.",
        "ask_last_period": (
            "📅 உங்கள் *கடந்த மாதவிடாய் தொடங்கிய தேதியை* தெரிவிக்கவும்.\n\n"
            "வடிவம்: `DD-MM-YYYY`\nஎடுத்துக்காட்டு: `15-03-2025`"
        ),
        "invalid_date": "❌ தேதி புரியவில்லை. `DD-MM-YYYY` வடிவத்தில் உள்ளிடவும்.",
        "future_date": "❌ தேதி எதிர்காலத்தில் இருக்க முடியாது.",
        "date_too_old": "❌ கடந்த 6 மாதங்களுக்குள்ளான தேதியை உள்ளிடவும்.",
        "prediction": (
            "🌸 *சுழற்சி கணிப்பு*\n\n"
            "📌 கடந்த மாதவிடாய்: *{last_period}*\n"
            "🔮 அடுத்த மாதவிடாய்: *{next_period}*\n"
            "📆 மீதமுள்ள நாட்கள்: *{days_remaining} நாட்கள்*\n\n"
            "இப்போது என்னிடம் எதையும் கேளுங்கள்! 💬\n\n"
            "_{cycle_length}-நாள் சுழற்சியை அடிப்படையாக கொண்ட மதிப்பீடு. மருத்துவ ஆலோசனைக்கு மருத்துவரை அணுகவும்._"
        ),
        "already_active": "தயாராக உள்ளது! எதையும் கேளுங்கள். 💬",
        "reset_info": "/start தட்டச்சு செய்து மீட்டமைக்கவும்.",
        "disclaimer": "_⚠️ நான் ஒரு AI உதவியாளர், மருத்துவர் அல்ல. மருத்துவ முடிவுகளுக்கு எப்போதும் மருத்துவரை அணுகவும்._",
        "ai_error": "இப்போது இணைப்பில் சிக்கல் உள்ளது. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும். 🙏",
        "db_error": "ஏதோ தவறு நடந்தது. மீண்டும் முயற்சிக்கவும்.",
        "language_unknown": "எண்ணில் பதில் சொல்லுங்கள்:\n1️⃣ English\n2️⃣ हिंदी\n3️⃣ தமிழ்\n4️⃣ తెలుగు",
    },
    "te": {
        "welcome": (
            "🌸 *నమస్కారం! నేను సఖి*, మీ వ్యక్తిగత ఋతుచక్ర ఆరోగ్య సహాయకురాలిని.\n\n"
            "నేను మీ చక్రాన్ని ట్రాక్ చేయడంలో, తదుపరి రుతుక్రమాన్ని అంచనా వేయడంలో "
            "మరియు ఆరోగ్య ప్రశ్నలకు సమాధానమివ్వడంలో సహాయపడతాను.\n\n"
            "దయచేసి మీ భాషను ఎంచుకోండి:\n"
            "1️⃣ English\n2️⃣ हिंदी (Hindi)\n3️⃣ தமிழ் (Tamil)\n4️⃣ తెలుగు (Telugu)"
        ),
        "language_set": "✅ సరే! భాష *తెలుగు*కు సెట్ చేయబడింది.",
        "ask_last_period": (
            "📅 మీ తదుపరి చక్రాన్ని అంచనా వేయడానికి, దయచేసి *మీ చివరి రుతుక్రమం ప్రారంభమైన తేదీని* తెలియజేయండి.\n\n"
            "ఆకృతి: `DD-MM-YYYY`\nఉదాహరణ: `15-03-2025`"
        ),
        "invalid_date": "❌ తేదీ అర్థం కాలేదు. దయచేసి `DD-MM-YYYY` ఆకృతిలో నమోదు చేయండి.\nఉదాహరణ: `15-03-2025`",
        "future_date": "❌ తేదీ భవిష్యత్తులో ఉండకూడదు. దయచేసి చెల్లుబాటు అయ్యే గత తేదీని నమోదు చేయండి.",
        "date_too_old": "❌ ఆ తేదీ చాలా పాతది. దయచేసి గత 6 నెలల్లోని తేదీని నమోదు చేయండి.",
        "prediction": (
            "🌸 *చక్ర అంచనా*\n\n"
            "📌 చివరి రుతుక్రమం ప్రారంభమైంది: *{last_period}*\n"
            "🔮 తదుపరి రుతుక్రమం అంచనా: *{next_period}*\n"
            "📆 మిగిలిన రోజులు: *{days_remaining} రోజులు*\n\n"
            "ఇప్పుడు మీరు నన్ను ఆరోగ్యం గురించి ఏదైనా అడగవచ్చు! 💬\n\n"
            "_{cycle_length}-రోజుల చక్రం ఆధారంగా ఇది అంచనా. వైద్య సలహా కోసం డాక్టర్‌ని సంప్రదించండి._"
        ),
        "already_active": "సిద్ధంగా ఉంది! మీ చక్రం లేదా ఆరోగ్యం గురించి ఏదైనా అడగండి. 💬",
        "reset_info": "మీ ప్రొఫైల్‌ని రీసెట్ చేయడానికి /start టైప్ చేయండి.",
        "disclaimer": "_⚠️ నేను AI సహాయకుడిని, వైద్యుడిని కాదు. వైద్య నిర్ణయాల కోసం ఎప్పుడూ అర్హత కలిగిన డాక్టర్‌ని సంప్రదించండి._",
        "ai_error": "ఇప్పుడు కనెక్ట్ చేయడంలో సమస్య ఉంది. దయచేసి కొంత సేపు తర్వాత మళ్ళీ ప్రయత్నించండి. 🙏\n\nత్వరగా పరిష్కరించుకోవాల్సిన విషయాలకు, ఆరోగ్య సేవా నిపుణుడిని సంప్రదించండి.",
        "db_error": "నా వైపు ఏదో తప్పు జరిగింది. దయచేసి కొంచెం సేపు తర్వాత మళ్ళీ ప్రయత్నించండి.",
        "language_unknown": (
            "దయచేసి సంఖ్యతో జవాబు ఇవ్వండి:\n1️⃣ English\n2️⃣ हिंदी\n3️⃣ தமிழ்\n4️⃣ తెలుగు"
        ),
    },
}


def get_message(lang: str, key: str, **kwargs: str) -> str:
    """Return a localised message, falling back to English."""
    lang = lang if lang in MESSAGES else "en"
    template = MESSAGES[lang].get(key, MESSAGES["en"].get(key, ""))
    if kwargs:
        return template.format(**kwargs)
    return template

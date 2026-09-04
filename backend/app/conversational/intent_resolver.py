"""Deterministic Intent Resolver and Context Disambiguation Engine for AgentGuard."""

import re
from typing import Any

from backend.app.conversational.models import (
    CanonicalTopic,
    ConversationAction,
    ConversationSession,
    ConversationTurn,
    ConversationalPurpose,
    DialogueAct,
    EntityReference,
    FollowUpSuggestion,
    LiveToolRequest,
    LiveToolType,
    ProgressiveDisclosureOffer,
    ResponsePlan,
    ResponseStrategy,
    TopicContext,
    UserIntentCategory,
)
from backend.app.retrieval.classifier import QueryClassifier
from backend.app.retrieval.models import QueryCategory, QueryClassification


class IntentResolver:
    """Resolves natural user queries into strongly-typed conversational intent plans,

    performing contextual pronoun/coreference resolution, topic tracking, purpose identification,
    response strategy selection, and deterministic static-vs-live routing.
    """

    ADVERSARIAL_PATTERNS = [
        r"ignore\s+(all\s+)?(previous\s+|prior\s+)?(instructions|rules|policy|policies|constraints|safeguards)",
        r"reveal\s+(the\s+)?(system\s+prompt|\.env|api[_\s]key|secret|credentials)",
        r"(show\s+me|give\s+me|reveal)\s+(the\s+)?(contents\s+of\s+)?\.env",
        r"bypass\s+(the\s+)?(firewall|policy|authorization|security)",
        r"(approve|execute|authorize|pay|process)\s+(this\s+|the\s+|a\s+|an\s+)?(purchase\s+order|order|transaction|payment|merchant\s+[0-9a-zA-Z_\-]+)(\s+for\s+me|\s+yourself)?",
        r"pretend\s+you\s+are|act\s+as(\s+an?)?\s+admin|roleplay\s+as|simulate\s+admin",
        r"\b(change|increase|decrease|reduce|lower|modify|alter|set|reset|raise|boost|extend|expand|update|adjust)\s+.*(the\s+|my\s+)?(mandate\s+)?(budget|limit|spending|cap|authority|allowance)\b",
        r"\b(modifying|altering|changing|increasing|decreasing|reducing|resetting|extending|adjusting)\s+.*(the\s+|my\s+)?(mandate\s+)?(budget|spending|limit|cap|authority)\b",
        r"\b(mandate\s+)?(budget|spending|limit|spending\s+cap|spending\s+authority|allowance)\s+(modification|alteration|change|adjustment|increase|decrease|reduction|extension|reset|override)\b",
        r"\b(attempting|requesting|initiating|performing|executing)\s+.*(budget|spending|mandate)\s+(modification|alteration|change|adjustment|increase|decrease|reduction|override|reset)\b",
        r"(disable|turn\s+off|skip)\s+(the\s+)?(policy\s+check|firewall|validation)",
        r"override\s+.*(rules|limits|budget|policy|safeguards|security|check)",
        r"(give\s+me|show\s+me|list|dump|exfiltrate)\s+.*(password|secret|key|api[_\s]key|token|credential)",
        r"forget\s+(the\s+)?(rules|instructions|policy|safeguards)",
        r"disregard\s+(the\s+)?(firewall|policy|rules)",
        r"pay\s+merchant\s+[0-9a-zA-Z_\-]+",
        r"execute\s+this\s+transaction(\s+for\s+me)?",
        r"(delete|erase|clear|wipe|remove|destroy|truncate|drop|reset|purge|alter|modify)\s+.*(audit|ledger|log|logs|history|records|forensic|chain|evidence|transaction\s+history)",
        r"(delete|erase|clear|wipe|remove|destroy|truncate|drop|reset|purge)\s+(the\s+)?(audit\s+history|audit\s+logs|audit\s+records|forensic\s+ledger|transaction\s+history|evidence|logs)",
    ]

    OUT_OF_SCOPE_PATTERNS = [
        # Astronomy & Space
        r"distance\s+between\s+(the\s+)?earth\s+and\s+(the\s+)?(sun|moon)",
        r"how\s+far\s+is\s+(the\s+)?(moon|sun|mars|jupiter)",
        r"distance\s+to\s+(the\s+)?(moon|sun|mars)",
        r"what\s+is\s+a\s+black\s+hole",
        r"\b(moon|sun|mars|jupiter|saturn|neptune|pluto|galaxy|black\s+hole)\b",
        # Sports & Games
        r"cricket(\s+match)?",
        r"football(\s+match)?",
        r"basketball|soccer|tennis|baseball",
        r"who\s+won(\s+the)?(\s+sports)?\s+(game|match|cup|tournament|race|league|championship|world\s+cup)",
        r"who\s+won",
        r"\b(sports?|football|cricket|basketball|soccer|tennis|baseball|game\s+last\s+night)\b",
        r"tell\s+me\s+something\s+about\s+cricket",
        r"sports\s+scores?",
        # Food & Cooking
        r"pasta\s+recipe",
        r"recipe\s+for",
        r"(how\s+to|how\s+do\s+i|how\s+can\s+i)\s+(cook|bake|make|prepare)\s+",
        r"cook\s+(pasta|pizza|rice|cake|food|dinner|lunch|breakfast|biryani)",
        r"how\s+do\s+i\s+cook\s+biryani",
        r"ingredients\s+for",
        r"\b(recipe|pasta|pizza|baking|cooking|culinary|biryani)\b",
        # Weather & Forecast
        r"weather(\s+in|\s+today|\s+forecast)?",
        r"what('s|\s+is)\s+today('s|\s+the|\s+tomorrow's|\s+the\s+weather\s+like)?\s*weather",
        r"what('s|\s+is)\s+the\s+weather\s+like",
        r"temperature\s+in",
        r"is\s+it\s+raining",
        # Entertainment & Humor
        r"tell\s+me\s+a\s+joke",
        r"make\s+me\s+laugh",
        r"sing\s+a\s+song",
        r"write\s+a\s+poem",
        r"tell\s+me\s+a\s+story",
        # General Knowledge & Trivia & Stocks & Politics
        r"capital\s+of\s+[a-zA-Z]+",
        r"who\s+is\s+(the\s+)?(president|prime\s+minister)\s+of",
        r"\b(trivia|facts?|trivia\s+facts?)\b",
        r"give\s+me\s+(some\s+)?(general\s+)?(trivia|facts)",
        r"apple('s|\s+)?stock\s+price",
        r"stock\s+price\s+of",
        r"fibonacci\s+program",
        r"write\s+a\s+python\s+fibonacci",
    ]

    LIVE_DATA_PATTERNS = [
        # Mandate budget queries
        (r"(how\s+much\s+)?(remaining\s+|current\s+|available\s+)?budget\s+(is\s+)?(left|remaining|available|on\s+mandate|for\s+mandate|of\s+mandate)", LiveToolType.MANDATE_BUDGET),
        (r"how\s+much\s+budget\s+(is\s+left|on\s+|for\s+|of\s+|remaining)", LiveToolType.MANDATE_BUDGET),
        (r"(current\s+|remaining\s+)?balance\s+(on|for|of)?", LiveToolType.MANDATE_BUDGET),
        (r"(is\s+(that|it)\s+enough\s+(for|to)|can\s+i\s+afford|can\s+we\s+afford)", LiveToolType.MANDATE_BUDGET),
        (r"(is|are)\s+(the\s+)?(current\s+|active\s+)?(mandate\s+)?budget\s+sufficient", LiveToolType.MANDATE_BUDGET),
        (r"sufficient\s+to\s+purchase", LiveToolType.MANDATE_BUDGET),
        (r"enough\s+to\s+buy", LiveToolType.MANDATE_BUDGET),
        (r"enough\s+for", LiveToolType.MANDATE_BUDGET),
        (r"what('s|\s+is)\s+(the\s+)?(current\s+)?budget", LiveToolType.MANDATE_BUDGET),
        (r"what('s|\s+is)\s+(the\s+)?current\s+status\s+of\s+(the\s+)?mandate", LiveToolType.MANDATE_BUDGET),
        (r"status\s+of\s+(the\s+)?mandate", LiveToolType.MANDATE_BUDGET),
        (r"how\s+much\s+money\s+(is\s+)?(left|remaining)", LiveToolType.MANDATE_BUDGET),

        # Product catalog queries
        (r"(what|which)\s+(products|items|goods)\s+(are\s+)?(currently\s+)?(available|in\s+stock|do\s+we\s+have|can\s+i\s+buy)", LiveToolType.PRODUCT_CATALOG),
        (r"what\s+products\s+are\s+currently\s+available", LiveToolType.PRODUCT_CATALOG),
        (r"products\s+are\s+currently\s+available", LiveToolType.PRODUCT_CATALOG),
        (r"(is|are)\s+.*(in\s+stock|left\s+in\s+catalog)", LiveToolType.PRODUCT_CATALOG),
        (r"(is|are)\s+(product\s+|item\s+)?[a-zA-Z0-9_\-]+\s+available\s+in\s+(catalog|stock)", LiveToolType.PRODUCT_CATALOG),
        (r"is\s+product\s+[a-zA-Z0-9_\-]+\s+in\s+stock", LiveToolType.PRODUCT_CATALOG),
        (r"how\s+many\s+units\s+(of\s+.*)?(left|in\s+stock)", LiveToolType.PRODUCT_CATALOG),
        (r"(what|which)\s+products\s+(are\s+)?(available|in\s+stock|do\s+we\s+have|can\s+i\s+buy)", LiveToolType.PRODUCT_CATALOG),
        (r"(show|list)\s+(me\s+)?(the\s+)?(products|catalog|items|inventory|available\s+products)", LiveToolType.PRODUCT_CATALOG),
        (r"(show|list|tell|give)\s+(me\s+)?(the\s+)?prices(\s+for\s+products|\s+of\s+products|\s+of\s+the\s+products|\s+in\s+the\s+catalog|\s+in\s+catalog)?", LiveToolType.PRODUCT_CATALOG),
        (r"prices\s+(for|of)\s+(the\s+)?products(\s+currently\s+in\s+the\s+catalog|\s+in\s+the\s+catalog|\s+in\s+catalog)?", LiveToolType.PRODUCT_CATALOG),
        (r"product\s+catalog\s+prices?", LiveToolType.PRODUCT_CATALOG),
        (r"what\s+can\s+i\s+buy", LiveToolType.PRODUCT_CATALOG),
        (r"what\s+are\s+the\s+(current\s+)?prices", LiveToolType.PRODUCT_CATALOG),
        (r"how\s+much\s+(is|are)\s+(the\s+)?(earbuds|speaker|headphones|products)", LiveToolType.PRODUCT_CATALOG),
        (r"price\s+of\s+(the\s+)?(earbuds|speaker|headphones)", LiveToolType.PRODUCT_CATALOG),
        (r"what('s|\s+is)\s+the\s+price\s+of", LiveToolType.PRODUCT_CATALOG),
        (r"what\s+products\s+are\s+available\s+and\s+what\s+are\s+their\s+prices", LiveToolType.PRODUCT_CATALOG),

        # Merchant queries
        (r"(what|which)\s+merchants\s+(are\s+)?(currently\s+)?(active|authorized|available|in\s+the\s+system|in\s+system)", LiveToolType.MERCHANT_CATALOG),
        (r"(show|list)\s+(me\s+)?(the\s+)?(active\s+)?merchants", LiveToolType.MERCHANT_CATALOG),
        (r"active\s+merchants", LiveToolType.MERCHANT_CATALOG),
        (r"what\s+merchants\s+do\s+we\s+have", LiveToolType.MERCHANT_CATALOG),
        (r"merchants\s+are\s+currently\s+active", LiveToolType.MERCHANT_CATALOG),

        # Ledger & Transaction queries
        (r"(show|list|tell)\s+(me\s+)?(what\s+happened\s+in\s+)?(the\s+)?(recent\s+)?transactions", LiveToolType.TRANSACTION_STATUS),
        (r"show\s+me\s+what\s+happened\s+in\s+(the\s+)?recent\s+transactions", LiveToolType.TRANSACTION_STATUS),
        (r"what\s+happened\s+in\s+(the\s+)?recent\s+transactions", LiveToolType.TRANSACTION_STATUS),
        (r"recent\s+transaction\s+history", LiveToolType.TRANSACTION_STATUS),
        (r"recent\s+transactions", LiveToolType.TRANSACTION_STATUS),
        (r"transaction\s+history", LiveToolType.TRANSACTION_STATUS),
        (r"how\s+many\s+transactions\s+.*(ledger|recorded|exist|in\s+database|in\s+system)", LiveToolType.TRANSACTION_STATUS),
        (r"how\s+many\s+transactions\s+(are\s+there|are\s+in\s+the\s+ledger|in\s+the\s+ledger|do\s+we\s+have|were\s+recorded|exist|are\s+recorded)", LiveToolType.TRANSACTION_STATUS),
        (r"how\s+many\s+records\s+(are\s+)?in\s+the\s+(forensic\s+)?ledger", LiveToolType.TRANSACTION_STATUS),
        (r"what('s|\s+is)\s+currently\s+in\s+the\s+(forensic\s+)?ledger", LiveToolType.TRANSACTION_STATUS),
        (r"show\s+me\s+the\s+recent\s+transaction", LiveToolType.TRANSACTION_STATUS),
        (r"are\s+there\s+any\s+transactions", LiveToolType.TRANSACTION_STATUS),
        (r"how\s+many\s+successful\s+transactions", LiveToolType.TRANSACTION_STATUS),
        (r"did\s+(the\s+|that\s+)?transaction(\s+[a-zA-Z0-9\-_]+)?\s+(go\s+through|succeed|pass|fail|execute)", LiveToolType.TRANSACTION_STATUS),
        (r"status\s+of\s+transaction(\s+[a-zA-Z0-9\-_]+)?", LiveToolType.TRANSACTION_STATUS),
        (r"live\s+.*audit\s+(chain|ledger)\s+validity", LiveToolType.AUDIT_CHAIN_INTEGRITY),
        (r"how\s+many\s+audit\s+events", LiveToolType.AUDIT_CHAIN_INTEGRITY),
    ]

    WALKTHROUGH_PATTERNS = [
        r"\b(walkthrough|walk\s+me\s+through|project\s+walkthrough|judge|evaluating\s+agentguard|2-minute|two-minute|two\s+minute|2\s+minute)\b",
        r"overview\s+of\s+(what\s+you('ve|\s+have)\s+built|the\s+whole\s+project|the\s+entire\s+project|the\s+whole\s+system|the\s+system|agentguard)",
        r"explain\s+(what\s+you('ve|\s+have)\s+built|the\s+project\s+end-to-end|the\s+whole\s+system|the\s+whole\s+project)",
        r"show\s+me\s+(how\s+(this|it)\s+works|the\s+whole\s+system|around\s+the\s+application|around\s+the\s+app|around)",
        r"demonstrate\s+agentguard",
        r"give\s+me\s+a\s+(quick\s+)?(2-minute|2\s+minute|two\s+minute|short)?\s*(walkthrough|overview|demo)",
        r"what\s+should\s+i\s+look\s+at(\s+in\s+the\s+ui)?",
        r"hackathon\s+(demo|evaluation|walkthrough|overview)",
    ]

    HUMAN_APPROVAL_PATTERNS = [
        r"(and\s+)?what\s+if\s+i\s+approve\s+it\s+manually",
        r"approve\s+it\s+manually",
        r"manual\s+approval",
        r"human\s+approval",
        r"approve\s+manually",
        r"if\s+i\s+approve\s+it",
        r"can\s+a\s+human\s+approve",
        r"supervisor\s+approval",
        r"human\s+in\s+the\s+loop",
        r"can\s+the\s+human\s+approve",
        r"what\s+if\s+the\s+user\s+approves",
    ]

    CODE_INQUIRY_PATTERNS = [
        r"where\s+(in\s+the\s+(code|codebase|source|repo|repository)\s+)?(is\s+)?(that|it|this)?(\s+(implemented|coded|defined|located|handled|written))?",
        r"where\s+in\s+the\s+(code|codebase|source|repo)",
        r"where\s+does\s+(that|it|this)\s+(live|happen|execute)",
        r"which\s+file\s+handles\s+(that|it|this)",
        r"what('s|\s+is)\s+responsible\s+for\s+(that|it|this)",
        r"which\s+function\s+does\s+(that|it|this)",
        r"(show|point)\s+me\s+to\s+(the\s+)?(code|source|implementation|file)",
        r"show\s+me\s+where\s+(that|it|this)\s+happens",
        r"can\s+you\s+point\s+me\s+to\s+the\s+code",
        r"where\s+is\s+that\s+(protection|check|safeguard)\s+implemented",
        r"where\s+was\s+that\s+protection\s+implemented",
        r"where\s+is\s+price\s+validation\s+implemented",
        r"where\s+is\s+replay\s+protection\s+implemented",
        r"where\s+is\s+the\s+audit\s+chain\s+implemented",
        r"where\s+is\s+the\s+policy\s+decision\s+made",
        r"where\s+is\s+budget\s+escalation\s+implemented",
        r"where\s+would\s+i\s+look\s+in\s+the\s+code",
    ]

    DEFINITION_PATTERNS = [
        r"what\s+is\s+(agentguard|the\s+agentic\s+commerce\s+firewall)",
        r"what('s|\s+is)\s+agentguard",
        r"what\s+exactly\s+is\s+agentguard",
        r"define\s+agentguard",
        r"explain\s+agentguard",
        r"can\s+you\s+explain\s+agentguard",
        r"tell\s+me\s+about\s+agentguard",
        r"what\s+kind\s+of\s+tool\s+is\s+agentguard",
        r"who\s+is\s+agentguard",
        r"basically,?\s*what\s+(exactly\s+)?is\s+(this\s+thing|agentguard|it)",
        r"what\s+(exactly\s+)?is\s+this\s+thing",
        r"explain\s+(agentguard|this|it)\s+to\s+someone\s+who\s+has\s+never\s+heard\s+of\s+it",
        r"explain\s+(agentguard|this|it)\s+to\s+a\s+(beginner|layman|child|5\s+year\s+old)",
        r"(give\s+me\s+)?(the\s+)?one[_\-\s]minute\s+explanation\s+(of\s+what\s+agentguard\s+is|of\s+agentguard|of\s+this)?",
        r"elevator\s+pitch\s+(for|of)\s+agentguard",
        r"in\s+(simple\s+terms|plain\s+english),?\s*what\s+is\s+agentguard",
        r"i'm\s+(hearing|new)\s+to\s+agentguard",
        r"so\s+basically,?\s*what\s+is\s+this\s+thing",
        r"give\s+me\s+the\s+short\s+version",
    ]

    FUNCTIONAL_PATTERNS = [
        r"what\s+(exactly|actually)\s+does\s+(this|agentguard|it)\s+do",
        r"what\s+does\s+(this|agentguard|it)\s+(actually|in\s+practice|operationally)\s+do",
        r"what\s+is\s+(the\s+)?(role|function|responsibility|job)\s+of\s+(this|agentguard)",
        r"what\s+role\s+does\s+(this|agentguard)\s+play",
        r"what\s+is\s+agentguard\s+responsible\s+for",
        r"what\s+happens\s+when\s+(an\s+agent|ai)\s+(tries\s+to\s+pay|uses\s+agentguard|proposes\s+a\s+purchase|makes\s+a\s+payment|tries\s+to\s+buy)",
        r"how\s+does\s+agentguard\s+intervene(\s+in\s+a\s+transaction)?",
        r"how\s+does\s+agentguard\s+sit\s+between",
        r"how\s+does\s+the\s+firewall\s+operate",
        r"what\s+does\s+it\s+actually\s+sit\s+between",
        r"can\s+you\s+explain\s+what\s+agentguard\s+(actually|specifically)\s+does",
        r"okay,?\s*but\s+what\s+(exactly\s+|actually\s+)?does\s+(agentguard|this|it)\s+do",
    ]

    VALUE_PROPOSITION_PATTERNS = [
        r"why\s+(would|should|do|does)\s+(anyone|someone|anybody|somebody|i|we|a\s+user|a\s+merchant|a\s+company|people|one)\s+(actually\s+|ever\s+|even\s+)?(need|use|want|care\s+about|buy|adopt)\s+(this|agentguard|it|something\s+like\s+this|a\s+system\s+like\s+this)",
        r"why\s+(would|should|do)\s+(i|we|anyone|someone)\s+(actually\s+|ever\s+)?(need|use|want)\s+(it|this|agentguard)",
        r"why\s+(is|are)\s+(this|agentguard|it)\s+(actually\s+)?(needed|necessary|useful|important|helpful)",
        r"what\s+(exact\s+|real\s+|actual\s+)?problem\s+does\s+(this|agentguard|it)\s+solve",
        r"what\s+kind\s+of\s+problem\s+is\s+agentguard\s+solving",
        r"what('s|\s+is)\s+the\s+(real\s+|actual\s+|main\s+)?(point|benefit|advantage|value|purpose)\s+of\s+(this|agentguard|the\s+system|something\s+like\s+this)",
        r"why\s+was\s+(this|agentguard|it)\s+(created|built|developed|designed)",
        r"why\s+it\s+was\s+built",
        r"why\s+did\s+you\s+(build|create|make)\s+this",
        r"what\s+makes\s+(this|agentguard)\s+(useful|necessary|valuable|special|unique)",
        r"what\s+value\s+does\s+(this|agentguard)\s+provide",
        r"why\s+should\s+i\s+care",
    ]

    COMPARISON_PATTERNS = [
        r"(how\s+is\s+(this|agentguard|it)|how\s+does\s+(this|agentguard|it)\s+compare)\s+(different\s+from|different\s+to|differ\s+from|compared\s+to)\s+(just\s+)?(doing\s+|using\s+)?(a\s+|the\s+)?(normal|standard|regular|conventional|traditional)?\s*(transaction|payment|gateway|checkout|payment\s+processor|razorpay|stripe)",
        r"how\s+is\s+(this|agentguard|it)\s+different",
        r"how\s+does\s+(this|agentguard|it)\s+differ",
        r"what('s|\s+is)\s+the\s+difference\s+between",
        r"why\s+not\s+just\s+(use\s+a\s+normal|do\s+normal|use\s+|call\s+)(payment|transaction|gateway|razorpay|stripe|paypal)",
        r"what('s|\s+is)\s+the\s+(real\s+|actual\s+)?advantage\s+(over|versus|vs)\s+(just\s+using\s+a\s+|a\s+|the\s+)?(normal|regular|standard|traditional)?\s*(payment\s+gateway|transaction|gateway|razorpay|stripe)",
        r"what\s+does\s+(agentguard|this|it)\s+add\s+(on\s+top\s+of|over|to)\s+(a\s+|the\s+)?(normal|standard|regular|conventional|traditional)?\s*(payment\s+)?(gateway|processor|razorpay|stripe|paypal|system)",
        r"why\s+can't\s+the\s+(payment\s+)?gateway\s+(itself\s+)?handle\s+this",
        r"why\s+can't\s+the\s+payment\s+provider\s+alone",
        r"why\s+can't\s+razorpay\s+just\s+do\s+this",
        r"why\s+can't\s+razorpay\s+handle\s+this",
        r"how\s+is\s+(this|agentguard)\s+different\s+from\s+(razorpay|stripe)",
        r"how\s+is\s+agentguard\s+different\s+from\s+razorpay",
    ]

    EXAMPLE_PATTERNS = [
        r"(give|show)\s+(me\s+)?(a\s+|an\s+)?(real\s+|realistic\s+|concrete\s+|practical\s+)?example",
        r"can\s+you\s+give\s+(me\s+)?(a\s+|an\s+)?(realistic\s+|real\s+|concrete\s+)?example(\s+scenario)?",
        r"can\s+you\s+give\s+(an?\s+)?example\s+scenario",
        r"example\s+scenario",
        r"walk\s+me\s+through\s+a\s+(real\s+|realistic\s+)?scenario",
        r"show\s+me\s+what\s+this\s+(would\s+)?look(s)?\s+like\s+in\s+practice",
        r"can\s+you\s+illustrate\s+that",
        r"give\s+me\s+a\s+concrete\s+situation",
        r"what\s+would\s+this\s+look\s+like\s+in\s+the\s+real\s+world",
    ]

    COUNTERFACTUAL_PATTERNS = [
        r"what\s+happens\s+if\s+agentguard\s+wasn't\s+there",
        r"what\s+if\s+agentguard\s+wasn't\s+there",
        r"what\s+if\s+the\s+attacker\s+changes\s+the\s+price",
        r"what\s+if\s+it\s+lies\s+about\s+the\s+price",
        r"what\s+if\s+the\s+ai\s+submits\s+a\s+(fake|cheaper|different)\s+amount",
        r"suppose\s+the\s+ai\s+submits\s+a\s+cheaper\s+amount",
        r"what\s+happens\s+if\s+someone\s+(replays|sends\s+the\s+same|tries\s+it\s+twice|tries\s+the\s+same)",
        r"what\s+happens\s+if\s+the\s+mandate\s+limit\s+is\s+exceeded",
        r"what\s+happens\s+if\s+the\s+price\s+changes",
        r"what\s+if\s+the\s+attacker\s+changes\s+it",
        r"what\s+happens\s+then",
    ]

    TIMING_PATTERNS = [
        r"is\s+that\s+(done\s+|checked\s+|performed\s+)?before\s+payment",
        r"is\s+the\s+check\s+done\s+before\s+payment",
        r"when\s+is\s+that\s+check\s+performed",
        r"does\s+that\s+happen\s+before\s+payment",
        r"before\s+or\s+after\s+payment",
    ]

    AFFIRMATIVE_TRIGGERS = [
        r"^(yes|yeah|sure|yep|yup|ok|okay|please|show\s+me|show\s+the\s+code|show\s+me\s+the\s+code|tell\s+me\s+more|go\s+ahead|do\s+it|show\s+code|view\s+code|i'd\s+like\s+that|let's\s+see\s+it|yes\s+please|show\s+the\s+details)$",
        r"^show\s+me\s+where",
        r"^explain\s+that\s+more",
    ]

    NEGATIVE_TRIGGERS = [
        r"^(no|nope|nah|not\s+now|not\s+that|no\s+thanks|skip\s+that|don't\s+show\s+me\s+that|forget\s+that|forget\s+it|cancel)[\.\!\?]?$",
        r"^(no,?\s+)?(don't\s+show\s+(me\s+)?that|not\s+that|no\s+thanks|don't\s+show\s+the\s+code)[\.\!\?]?$",
        r"^(no\s+thanks,?\s+)?don't\s+show\s+the\s+code\.?\s+let's\s+switch.*",
        r"^forget\s+(that\s+topic|the\s+code|security)",
        r"^(no,?\s+)?(let's\s+switch\s+to|switch\s+to)",
        r"^tell\s+me\s+something\s+else",
        r"^let's\s+talk\s+about\s+something\s+else",
    ]

    def __init__(self, query_classifier: QueryClassifier | None = None) -> None:
        self.classifier = query_classifier or QueryClassifier()

    def _extract_active_query_text(self, lower: str) -> tuple[str, list[str]]:
        """Extracts the active query text by stripping out negative pivot clauses and returning abandoned keywords."""
        abandoned_clauses: list[str] = []
        clean_text = lower

        pivot_patterns = [
            r"\b(?:okay\s+|ok\s+|actually\s+|wait\s+)?(?:forget|forget\s+about|put\s+aside|leave\s+aside|moving\s+on\s+from|instead\s+of|ignore|let\'?s\s+move\s+away\s+from|never\s+mind\s+about)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)(?=\s+(?:tell\s+me|what\s+about|how\s+about|and\s+discuss|and\s+explain|and\s+talk|let\'?s\s+discuss|let\'?s\s+talk|talk\s+about|discuss|i\s+want\s+to|what\s+happens|explain|how\s+does|is\s+there)|for\s+a\s+second|for\s+now|for\s+a\s+moment|,|\.|\?|$)",
            r"\b(?:not|no\s+not)\s+(?:the\s+)?(product\s+price|price\s+tampering|price|audit\s+chain|replay\s+attacks?|mandate\s+budget|threat\s+lab)(?:,|\.|\?|\s+what\s+about|\s+tell\s+me|\s+how\s+does|$)",
        ]
        for pat in pivot_patterns:
            for match in re.finditer(pat, clean_text, flags=re.IGNORECASE):
                abandoned_text = match.group(1).strip() if match.groups() else ""
                if abandoned_text:
                    abandoned_clauses.append(abandoned_text.lower())
                clean_text = clean_text.replace(match.group(0), " ").strip()

        clean_text = re.sub(r"^[\s,.\-!?:;]+|^(?:and|then|so|but)\s+", "", clean_text, flags=re.IGNORECASE).strip()
        clean_text = re.sub(r"^[\s,.\-!?:;]+", "", clean_text).strip()

        return clean_text, abandoned_clauses

    def resolve(self, query: str, session: ConversationSession | None = None) -> ResponsePlan:
        """Processes a query in the context of an optional session and generates a ResponsePlan."""
        trimmed = query.strip()
        lower = trimmed.lower()

        # 1. Check Adversarial / Injection attempts first
        for pat in self.ADVERSARIAL_PATTERNS:
            if re.search(pat, lower):
                subtype = "GENERAL"
                if re.search(r"(approve|execute|authorize|pay)\s+(this\s+|the\s+)?(transaction|payment|merchant)", lower):
                    subtype = "TRANSACTION_APPROVAL"
                elif re.search(
                    r"\b(change|increase|decrease|reduce|lower|modify|alter|set|reset|raise|boost|extend|expand|update|adjust)\s+.*(the\s+|my\s+)?(mandate\s+)?(budget|limit|spending|cap|authority|allowance)\b|"
                    r"\b(mandate\s+)?(budget|spending|limit|spending\s+cap|spending\s+authority|allowance)\s+(modification|alteration|change|adjustment|increase|decrease|reduction|extension|reset|override)\b|"
                    r"\b(attempting|requesting|initiating|performing|executing)\s+.*(budget|spending|mandate)\s+(modification|alteration|change)\b",
                    lower,
                ):
                    subtype = "BUDGET_MODIFICATION"
                elif re.search(r"(reveal|give\s+me|show\s+me)\s+.*(key|secret|\.env|credentials)", lower):
                    subtype = "CREDENTIAL_EXFILTRATION"
                elif re.search(r"(bypass|disable|turn\s+off|skip)\s+.*(firewall|policy|validation|authorization)", lower):
                    subtype = "FIREWALL_BYPASS"
                elif re.search(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|rules)", lower):
                    subtype = "PROMPT_INJECTION"

                return ResponsePlan(
                    intent=UserIntentCategory.ADVERSARIAL_INJECTION,
                    dialogue_act=DialogueAct.REFUSE_ADVERSARIAL,
                    purpose=ConversationalPurpose.ADVERSARIAL,
                    strategy=ResponseStrategy.REFUSE_ADVERSARIAL,
                    canonical_topic=CanonicalTopic.GENERAL_ARCHITECTURE,
                    strategy_rationale=f"TYPE:{subtype}",
                    resolved_query=trimmed,
                    needs_static_retrieval=False,
                    needs_live_tool=False,
                    is_adversarial=True,
                    adversarial_reason=f"Matched adversarial pattern '{pat}' (subtype: {subtype})",
                )

        # 2. Check Out-of-Scope inquiries
        for pat in self.OUT_OF_SCOPE_PATTERNS:
            if re.search(pat, lower) and not any(k in lower for k in ["agentguard", "mandate", "firewall", "razorpay"]):
                return ResponsePlan(
                    intent=UserIntentCategory.OUT_OF_SCOPE,
                    dialogue_act=DialogueAct.REFUSE_OUT_OF_SCOPE,
                    purpose=ConversationalPurpose.OUT_OF_SCOPE,
                    strategy=ResponseStrategy.REFUSE_OUT_OF_SCOPE,
                    canonical_topic=CanonicalTopic.GENERAL_ARCHITECTURE,
                    strategy_rationale="Polite redirection to specialized AgentGuard commerce firewall topics.",
                    resolved_query=trimmed,
                    needs_static_retrieval=False,
                    needs_live_tool=False,
                )

        # 3. Check Negative / Topic-Switch triggers (when pure rejection/reset)
        for pat in self.NEGATIVE_TRIGGERS:
            if re.search(pat, lower):
                remainder = re.sub(pat, "", trimmed, flags=re.IGNORECASE).strip(" ,.-")
                if not remainder or len(remainder) < 3:
                    return ResponsePlan(
                        intent=UserIntentCategory.TOPIC_SWITCH,
                        dialogue_act=DialogueAct.INFORM,
                        purpose=ConversationalPurpose.TOPIC_SWITCH,
                        strategy=ResponseStrategy.CHANGE_TOPIC,
                        canonical_topic=CanonicalTopic.GENERAL_ARCHITECTURE,
                        strategy_rationale="User declined offer or requested clean topic reset.",
                        resolved_query="Topic acknowledged. What would you like to explore next in AgentGuard?",
                        needs_static_retrieval=False,
                        needs_live_tool=False,
                        progressive_stage="OFFER_DECLINED",
                    )
                lower = remainder.lower()
                trimmed = remainder

        # 4. Check Progressive Disclosure Affirmation triggers
        if session and session.pending_progressive_offer:
            for pat in self.AFFIRMATIVE_TRIGGERS:
                if re.search(pat, lower):
                    offer = session.pending_progressive_offer
                    return self._resolve_progressive_affirmation(offer, session)

        # Extract active query text and abandoned clauses for negative pivot handling
        clean_text, abandoned_clauses = self._extract_active_query_text(lower)
        active_trimmed = clean_text if (clean_text and abandoned_clauses) else trimmed
        active_lower = active_trimmed.lower()

        # 5. Topic Resolution (Identify active or switched canonical topic with negative pivot filtering)
        canonical_topic = self._identify_topic(lower, session)

        # 6. Purpose & Strategy Inference
        purpose, strategy = self._infer_purpose_and_strategy(active_lower if abandoned_clauses else lower, canonical_topic, session)

        # 7. Contextual Query Disambiguation (Pronoun & Subject Resolution + Compound Query Preservation)
        resolved_query = self._resolve_contextual_query(active_trimmed if abandoned_clauses else trimmed, purpose, canonical_topic, session)

        # Check for compound query sub-intents (strictly disabled when negative pivot occurs)
        is_compound = (
            (" and " in lower or "; " in lower or ". also" in lower or ", and " in lower or "? and " in lower or "? also" in lower or ", also" in lower or " also " in lower or " but " in lower or " while " in lower or " plus " in lower)
            and len(trimmed.split()) > 5
            and not bool(abandoned_clauses)
        )
        sub_intents: list[dict[str, Any]] = []
        if is_compound:
            if any(w in lower for w in ["price tampering", "price manipulation", "tamper", "claim diff", "price check", "fake price", "price mismatch", "price verification"]):
                sub_intents.append({"intent": UserIntentCategory.PRICE_TAMPERING.value, "topic": "PRICE_TAMPERING", "clause": "price tampering detection"})
            if any(w in lower for w in ["merchant scope", "unauthorized merchant", "authorized merchant", "merchant authorization"]):
                sub_intents.append({"intent": UserIntentCategory.CONCEPT_EXPLANATION.value, "topic": "MERCHANT_SCOPE", "clause": "merchant scope authorization"})
            if any(w in lower for w in ["live protection", "dual-chamber", "firewall protection", "live defense", "firewall"]):
                sub_intents.append({"intent": UserIntentCategory.LIVE_PROTECTION.value, "topic": "LIVE_PROTECTION", "clause": "live protection impact"})
            if any(w in lower for w in ["mandate budget", "spending limit", "spending cap", "budget"]):
                sub_intents.append({"intent": UserIntentCategory.MANDATE_BUDGET.value, "topic": "MANDATE_BUDGET", "clause": "mandate budget"})
            if any(w in lower for w in ["replay", "idempotency", "duplicate", "repeat payment", "repeated payment", "same payment"]):
                sub_intents.append({"intent": UserIntentCategory.REPLAY_ATTACK.value, "topic": "REPLAY_ATTACK", "clause": "replay attack prevention"})
            if any(w in lower for w in ["audit chain", "audit ledger", "sha-256", "hash chain", "forensic ledger", "audit trail", "audit"]):
                sub_intents.append({"intent": UserIntentCategory.AUDIT_CHAIN.value, "topic": "AUDIT_CHAIN", "clause": "cryptographic audit trail"})

        # 8. Deterministic Static vs Live Routing Check
        live_tool_request = self._check_live_routing(resolved_query, session, lower)
        if live_tool_request:
            is_pure_live = any(k in lower for k in ["what products are", "products are available", "what merchants", "active merchants", "recent transactions", "transaction history", "how much budget", "current budget", "balance"])
            intent_val = UserIntentCategory.LIVE_DATA_QUERY if is_pure_live else (sub_intents[0]["intent"] if (is_compound and sub_intents) else UserIntentCategory.LIVE_DATA_QUERY)
            return ResponsePlan(
                intent=intent_val,
                dialogue_act=DialogueAct.LIVE_STATUS,
                purpose=ConversationalPurpose.LIVE_STATE_REQUEST if not is_compound else purpose,
                strategy=ResponseStrategy.REPORT_LIVE_STATE if not is_compound else strategy,
                canonical_topic=canonical_topic,
                strategy_rationale="Fetch live state from PostgreSQL database.",
                resolved_query=resolved_query,
                needs_static_retrieval=is_compound,
                needs_live_tool=True,
                live_tool_request=live_tool_request,
                compound_query=is_compound,
                sub_intents=sub_intents,
            )

        # 9. Classification via B-2 QueryClassifier
        classification = self.classifier.classify(resolved_query)

        # Dynamic live check from classifier (Only if purpose is not UI navigation or code reference or walkthrough)
        if (
            purpose not in (ConversationalPurpose.UI_NAVIGATION_REQUEST, ConversationalPurpose.CODE_LOCATION_REQUEST, ConversationalPurpose.CLARIFICATION, ConversationalPurpose.PROJECT_WALKTHROUGH)
            and classification.is_dynamic_live
            and classification.dynamic_action
            and any(w in lower for w in ["budget", "balance", "how much", "status", "stock", "did transaction", "in stock", "available", "products", "prices", "merchants", "ledger", "transactions"])
        ):
            live_type = self._map_resource_to_live_tool(classification.dynamic_action.target_resource)
            params: dict[str, Any] = {"query": resolved_query}
            m_match = re.search(r"mandate-[0-9a-zA-Z_\-]+", lower)
            if m_match:
                params["mandate_id"] = m_match.group(0)
            t_match = re.search(r"txn-[0-9a-zA-Z_\-]+", lower)
            if t_match:
                params["transaction_id"] = t_match.group(0)
            p_match = re.search(r"prod-[0-9a-zA-Z_\-]+", lower)
            if p_match:
                params["product_id"] = p_match.group(0)

            intent_val = sub_intents[0]["intent"] if (is_compound and sub_intents) else UserIntentCategory.LIVE_DATA_QUERY
            return ResponsePlan(
                intent=intent_val,
                dialogue_act=DialogueAct.LIVE_STATUS,
                purpose=ConversationalPurpose.LIVE_STATE_REQUEST if not is_compound else purpose,
                strategy=ResponseStrategy.REPORT_LIVE_STATE if not is_compound else strategy,
                canonical_topic=canonical_topic,
                strategy_rationale=f"Dynamic safeguard matched: {classification.dynamic_action.target_resource}",
                resolved_query=resolved_query,
                needs_static_retrieval=is_compound,
                needs_live_tool=True,
                live_tool_request=LiveToolRequest(
                    tool_type=live_type,
                    parameters=params,
                    reason=classification.dynamic_action.reason,
                ),
                compound_query=is_compound,
                sub_intents=sub_intents,
            )

        # 10. Intent and Dialogue Act Mapping
        intent, act = self._map_classification_to_intent(classification, lower, resolved_query, purpose, canonical_topic)
        if is_compound and sub_intents:
            intent = sub_intents[0]["intent"]

        # 11. UI Action Recommendation
        suggested_action = self._detect_ui_action(resolved_query, intent, canonical_topic, session)

        return ResponsePlan(
            intent=intent,
            dialogue_act=act,
            purpose=purpose,
            strategy=strategy,
            canonical_topic=canonical_topic,
            strategy_rationale=f"Execute {strategy.value} for {canonical_topic.value} addressing {purpose.value}.",
            resolved_query=resolved_query,
            needs_static_retrieval=True,
            needs_live_tool=False,
            suggested_action=suggested_action,
            compound_query=is_compound,
            sub_intents=sub_intents,
        )

    def _identify_topic(self, lower: str, session: ConversationSession | None) -> CanonicalTopic:
        """Determines the active canonical topic for the current turn with negative pivot isolation."""
        clean_text, abandoned_clauses = self._extract_active_query_text(lower)
        active_lower = clean_text.lower() if clean_text else lower

        # 1. Topic Reversion check in active text
        if any(w in active_lower for w in ["go back to", "back to", "return to"]):
            if "price" in active_lower:
                return CanonicalTopic.PRICE_TAMPERING
            if any(k in active_lower for k in ["replay", "duplicate", "repeat", "same request", "same payment"]):
                return CanonicalTopic.REPLAY_ATTACK
            if "audit" in active_lower or "ledger" in active_lower:
                return CanonicalTopic.AUDIT_CHAIN
            if "budget" in active_lower or "mandate" in active_lower:
                return CanonicalTopic.MANDATE_BUDGET
            if "merchant" in active_lower:
                return CanonicalTopic.MERCHANT_SCOPE
            if session and session.topic_history:
                return session.topic_history[-1].canonical_topic

        # 2. Explicit keywords in active query (prioritizing new subject over abandoned topic)
        if any(k in active_lower for k in [
            "replay", "idempotency", "duplicate execution", "same payment request twice",
            "same request twice", "same transaction twice", "sends the same", "send the same",
            "send it twice", "tries twice", "double charge", "duplicate payment", "duplicate debit",
            "repeat payment", "repeated payment", "repeat transaction", "repeated transaction",
            "duplicate transaction", "replayed transaction", "same payment twice", "payment replay",
            "replay protection", "preventing double payment", "prevent double payment",
            "preventing duplicate execution", "prevent duplicate payment", "double billing",
            "repeat payment protection", "repeat payment prevention", "replay attacks"
        ]):
            return CanonicalTopic.REPLAY_ATTACK

        if any(k in active_lower for k in [
            "audit", "hash chain", "ledger", "sha-256", "sha256", "audit chain", "audit record",
            "forensic ledger", "tamper with audit", "tamper with the record", "audit_log.py"
        ]):
            return CanonicalTopic.AUDIT_CHAIN

        if "engine.py" in active_lower or "policy/engine" in active_lower:
            return CanonicalTopic.PRICE_TAMPERING

        if "execute.py" in active_lower:
            return CanonicalTopic.REPLAY_ATTACK

        if any(k in active_lower for k in [
            "price tampering", "price manipulation", "price mismatch", "claim diff",
            "catalog price", "wrong price", "fake price", "tampered price", "lies about the price",
            "claims the earbuds", "claims the price", "claims it costs", "cost ₹", "costs ₹",
            "price of ₹", "claims ₹", "lies about", "claims the item", "claims the"
        ]):
            return CanonicalTopic.PRICE_TAMPERING

        if any(k in active_lower for k in [
            "budget", "mandate", "spending limit", "spending cap", "budget shortfall",
            "over budget", "over-budget"
        ]):
            return CanonicalTopic.MANDATE_BUDGET

        if any(k in active_lower for k in ["threat lab", "simulate", "threat scenario", "attack simulation"]):
            return CanonicalTopic.THREAT_LAB

        if any(k in active_lower for k in ["forensic", "forensics"]):
            return CanonicalTopic.FORENSIC_LEDGER

        if any(k in active_lower for k in ["merchant", "unauthorized merchant", "merchant scope"]):
            return CanonicalTopic.MERCHANT_SCOPE

        # Price fallback keyword if in active_lower and NOT in abandoned clauses
        if "price" in active_lower and not any("price" in c for c in abandoned_clauses):
            return CanonicalTopic.PRICE_TAMPERING

        # 3. If word "tamper" appears: check context
        if "tamper" in active_lower:
            if "audit" in active_lower or "record" in active_lower or "ledger" in active_lower or "hash" in active_lower:
                return CanonicalTopic.AUDIT_CHAIN
            if session and session.active_topic and session.active_topic.canonical_topic in (CanonicalTopic.AUDIT_CHAIN, CanonicalTopic.FORENSIC_LEDGER):
                return session.active_topic.canonical_topic
            if not any("price" in c for c in abandoned_clauses):
                return CanonicalTopic.PRICE_TAMPERING

        # 4. If active text is empty or pronouns only, inherit from active session if present
        if session and session.active_topic:
            # If current active topic was explicitly abandoned, don't inherit it
            abandoned_topic = any(
                session.active_topic.canonical_topic.value.lower() in c
                or ("price" in c and session.active_topic.canonical_topic == CanonicalTopic.PRICE_TAMPERING)
                for c in abandoned_clauses
            )
            if not abandoned_topic:
                return session.active_topic.canonical_topic

        return CanonicalTopic.GENERAL_ARCHITECTURE

    def _infer_purpose_and_strategy(
        self, lower: str, canonical_topic: CanonicalTopic, session: ConversationSession | None
    ) -> tuple[ConversationalPurpose, ResponseStrategy]:
        """Infers communicative purpose and response strategy."""
        # 1. Project Walkthrough / Judge Demo requests
        for pat in self.WALKTHROUGH_PATTERNS:
            if re.search(pat, lower):
                return ConversationalPurpose.PROJECT_WALKTHROUGH, ResponseStrategy.WALKTHROUGH

        # 2. Human / Manual Approval Inquiries
        for pat in self.HUMAN_APPROVAL_PATTERNS:
            if re.search(pat, lower):
                return ConversationalPurpose.HUMAN_APPROVAL_INQUIRY, ResponseStrategy.EXPLAIN_HUMAN_APPROVAL

        # 3. Timing questions
        for pat in self.TIMING_PATTERNS:
            if re.search(pat, lower):
                return ConversationalPurpose.TIMING_CHECK, ResponseStrategy.EXPLAIN_TIMING

        # 4. Counterfactuals
        for pat in self.COUNTERFACTUAL_PATTERNS:
            if re.search(pat, lower):
                return ConversationalPurpose.COUNTERFACTUAL, ResponseStrategy.EXPLAIN_COUNTERFACTUAL

        # 5. Comparison / Differentiation
        for pat in self.COMPARISON_PATTERNS:
            if re.search(pat, lower):
                return ConversationalPurpose.COMPARISON, ResponseStrategy.DIFFERENTIATE

        # 6. Value Proposition / Problem / Why Needed
        for pat in self.VALUE_PROPOSITION_PATTERNS:
            if re.search(pat, lower):
                return ConversationalPurpose.VALUE_PROPOSITION, ResponseStrategy.EXPLAIN_WHY

        # 7. Functional Role / Operational Flow
        for pat in self.FUNCTIONAL_PATTERNS:
            if re.search(pat, lower):
                return ConversationalPurpose.FUNCTIONAL_EXPLANATION, ResponseStrategy.EXPLAIN_FUNCTION

        # 8. Explicit Definition / Identity
        for pat in self.DEFINITION_PATTERNS:
            if re.search(pat, lower):
                return ConversationalPurpose.INFORMATION_REQUEST, ResponseStrategy.INTRODUCE

        # 9. Concrete Example Request
        for pat in self.EXAMPLE_PATTERNS:
            if re.search(pat, lower):
                return ConversationalPurpose.EXAMPLE_REQUEST, ResponseStrategy.GIVE_EXAMPLE

        # 10. UI Navigation Request (Excluding transaction history inquiries)
        if any(w in lower for w in [
            "which page", "which tab", "where in the ui", "where in the app", "show me the page",
            "take me to", "in the ui", "in the app", "on the ui", "appears in the ui", "on the frontend",
            "can i see it in the ui", "show me the forensic", "show me the transaction involved", "show me what happened",
            "relevant page", "navigation", "navigation suggestions", "action hints", "application surfaces", "surfaces",
        ]) and not any(w in lower for w in ["recent transactions", "transaction history", "what happened in the recent transactions", "show me what happened in the recent"]):
            return ConversationalPurpose.UI_NAVIGATION_REQUEST, ResponseStrategy.PROVIDE_UI_LOCATION

        # 11. Code Location Request
        for pat in self.CODE_INQUIRY_PATTERNS:
            if re.search(pat, lower):
                return ConversationalPurpose.CODE_LOCATION_REQUEST, ResponseStrategy.PROVIDE_CODE_LOCATION

        # 12. Mechanism / How question / Bypass
        if any(w in lower for w in [
            "how does", "how do", "how is", "how exactly", "how can", "under the hood",
            "how to", "bypass", "how the", "how it",
        ]):
            return ConversationalPurpose.HOW_QUESTION, ResponseStrategy.EXPLAIN_HOW

        # 13. Rationale / Why question (within topic)
        if any(w in lower for w in [
            "why is that", "why does that", "why would that", "why are they", "why should i",
            "what's the risk", "whats the risk", "what could go wrong", "why it matters",
            "why does this matter", "why is it dangerous", "why can't gemini", "why cant gemini",
        ]) or lower.startswith("why "):
            return ConversationalPurpose.WHY_QUESTION, ResponseStrategy.EXPLAIN_WHY

        # 14. Clarification
        if any(w in lower for w in ["without the code", "explain simply", "conceptually", "in plain english"]):
            return ConversationalPurpose.CLARIFICATION, ResponseStrategy.CLARIFY

        # 15. Follow-up / Tell me more
        if any(w in lower for w in ["tell me more", "what about", "continue", "deep dive"]):
            return ConversationalPurpose.FOLLOW_UP, ResponseStrategy.DEEPEN

        return ConversationalPurpose.INFORMATION_REQUEST, ResponseStrategy.INTRODUCE

    def _resolve_contextual_query(
        self,
        trimmed: str,
        purpose: ConversationalPurpose,
        topic: CanonicalTopic,
        session: ConversationSession | None,
    ) -> str:
        """Resolves pronouns, coreferences, and context into a self-contained query grounded in the active topic."""
        lower = trimmed.lower()

        # Handle walkthrough queries
        if purpose == ConversationalPurpose.PROJECT_WALKTHROUGH:
            return "Give a comprehensive 2-minute project walkthrough of AgentGuard, including problem solved, dual-loop security architecture, core verification mechanisms, and recommended UI demo path."

        # Handle human/manual approval queries
        if purpose == ConversationalPurpose.HUMAN_APPROVAL_INQUIRY:
            return "How does manual human approval work in AgentGuard for policy decisions and budget shortfalls?"

        # Handle compound or multi-clause questions that should preserve their rich structure
        is_compound = (
            (" and " in lower or "; " in lower or ". also" in lower or ", and " in lower or "? and " in lower or "? also" in lower or " but " in lower)
            and len(trimmed.split()) > 5
        )
        if is_compound:
            return trimmed

        # Handle explicit questions that don't need resolution
        if len(trimmed.split()) > 7 and not any(w in lower for w in ["that", "this", "it", "the protection", "the check", "the attack"]):
            return trimmed

        # Contextual mapping per Purpose & Topic
        if purpose == ConversationalPurpose.WHY_QUESTION:
            if "gemini" in lower:
                return "Why can't Gemini directly spend the money?"
            if topic == CanonicalTopic.PRICE_TAMPERING:
                return "Why is price tampering dangerous and what is the untrusted client risk in AgentGuard?"
            elif topic == CanonicalTopic.REPLAY_ATTACK:
                return "Why are replay attacks dangerous and how do duplicate execution requests risk double charging?"
            elif topic == CanonicalTopic.AUDIT_CHAIN:
                return "Why does the cryptographic SHA-256 audit ledger matter for non-repudiation and tamper evidence?"
            elif topic == CanonicalTopic.MANDATE_BUDGET:
                return "Why do mandate spending limits matter and how do they prevent runaway AI budget drift?"
            elif topic == CanonicalTopic.MERCHANT_SCOPE:
                return "Why is merchant scope validation necessary to prevent unauthorized merchant charges?"
            return "Why is AgentGuard necessary to secure autonomous AI commerce transactions?"

        elif purpose == ConversationalPurpose.HOW_QUESTION:
            if "bypass" in lower:
                return f"Can an attacker or untrusted AI agent bypass {topic.value} protections in AgentGuard?"
            if "prove" in lower and "tamper" in lower:
                return "How does the cryptographic audit ledger prove tampering through SHA-256 hash chaining?"
            if "prompt injection" in lower:
                return "How does AgentGuard protect against prompt injection from the shopping agent?"
            if topic == CanonicalTopic.PRICE_TAMPERING:
                return "How does AgentGuard prevent price tampering through Claim Diff catalog validation in evaluate_policy()?"
            elif topic == CanonicalTopic.REPLAY_ATTACK:
                return "How does AgentGuard prevent replay attacks using database-backed idempotency key verification in execute.py?"
            elif topic == CanonicalTopic.AUDIT_CHAIN:
                return "How does the cryptographic audit ledger verify tamper-evidence through SHA-256 hash chaining in verify_audit_chain()?"
            elif topic == CanonicalTopic.MANDATE_BUDGET:
                return "How does AgentGuard enforce mandate budget limits and escalate budget shortfalls in evaluate_policy()?"
            elif topic == CanonicalTopic.MERCHANT_SCOPE:
                return "How does AgentGuard verify merchant scope against authorized merchants in evaluate_policy()?"
            return "How does the AgentGuard dual-loop firewall verify purchase proposal claims before payment?"

        elif purpose == ConversationalPurpose.EXAMPLE_REQUEST:
            if topic == CanonicalTopic.PRICE_TAMPERING:
                return "Can you give a realistic example of price tampering detection on Wireless Earbuds?"
            elif topic == CanonicalTopic.REPLAY_ATTACK:
                return "Can you give a realistic example of a duplicate payment replay attack rejection?"
            elif topic == CanonicalTopic.AUDIT_CHAIN:
                return "Can you give a realistic example of detecting a broken SHA-256 hash chain in the audit ledger?"
            elif topic == CanonicalTopic.MANDATE_BUDGET:
                return "Can you give a realistic example of budget shortfall escalation for a purchase exceeding mandate limits?"
            return "Can you give a realistic example of an end-to-end AgentGuard shopping proposal and firewall decision?"

        elif purpose == ConversationalPurpose.CODE_LOCATION_REQUEST:
            if "engine.py" in lower:
                return "Where is policy evaluation and security validation implemented in backend/app/policy/engine.py?"
            if "execute.py" in lower:
                return "Where is replay attack protection implemented in backend/app/api/execute.py?"
            if "audit_log.py" in lower:
                return "Where is cryptographic audit chain verification implemented in backend/app/services/audit_log.py?"
            if "propose.py" in lower:
                return "Where is purchase proposal validation implemented in backend/app/api/propose.py?"
            if topic == CanonicalTopic.PRICE_TAMPERING or "price" in lower or "claim diff" in lower or "mismatch" in lower:
                return "Where is price tampering validation implemented in backend/app/policy/engine.py and propose.py?"
            elif topic == CanonicalTopic.REPLAY_ATTACK or "replay" in lower:
                return "Where is replay attack protection implemented in backend/app/api/execute.py?"
            elif topic == CanonicalTopic.AUDIT_CHAIN or "audit" in lower or "hash" in lower or "ledger" in lower:
                return "Where is cryptographic audit chain verification implemented in backend/app/services/audit_log.py?"
            elif topic == CanonicalTopic.MANDATE_BUDGET or "budget" in lower or "mandate" in lower:
                return "Where is mandate budget evaluation implemented in backend/app/policy/engine.py and routes_mandate.py?"
            if trimmed.strip("? .") in ["where is that", "where is it", "where does that live"]:
                return "Where is the core policy engine and firewall verification implemented in the codebase?"
            return "Where is the dual-loop firewall boundary implemented in backend/app/api/propose.py and execute.py?"

        elif purpose == ConversationalPurpose.UI_NAVIGATION_REQUEST:
            if topic == CanonicalTopic.PRICE_TAMPERING or "defense" in lower:
                return "Which tab in the UI displays real-time price tampering firewall decisions and Claim Diff?"
            elif topic == CanonicalTopic.REPLAY_ATTACK or topic == CanonicalTopic.THREAT_LAB or "threat" in lower:
                return "Which tab in the UI allows simulating replay attacks and threat scenarios?"
            elif topic == CanonicalTopic.AUDIT_CHAIN or topic == CanonicalTopic.FORENSIC_LEDGER or "audit" in lower or "forensic" in lower:
                return "Which tab in the UI displays the cryptographic SHA-256 forensic audit ledger?"
            elif topic == CanonicalTopic.MANDATE_BUDGET or "cockpit" in lower:
                return "Which tab in the UI displays live mandate budgets and spending limits?"
            return "What interactive tabs and surfaces are available in the AgentGuard UI?"

        elif purpose == ConversationalPurpose.COUNTERFACTUAL:
            if "wasn't there" in lower or "without agentguard" in lower:
                return "What would happen during an AI purchase if AgentGuard was not in place?"
            elif topic == CanonicalTopic.PRICE_TAMPERING or "price" in lower or "lies about" in lower or "claims" in lower or "1999" in lower or "1,999" in lower or "earbud" in lower:
                return "What happens if an attacker or agent manipulates the price or claims a lower price mid-flight?"
            elif topic == CanonicalTopic.REPLAY_ATTACK or "replay" in lower or "twice" in lower or "same request" in lower:
                return "What happens if someone attempts to execute the same transaction twice?"
            elif topic == CanonicalTopic.MANDATE_BUDGET or "budget" in lower:
                return "What happens if a purchase proposal exceeds the remaining mandate budget?"
            return "What happens if an untrusted shopping agent submits an invalid purchase claim?"

        elif purpose == ConversationalPurpose.TIMING_CHECK:
            if topic == CanonicalTopic.PRICE_TAMPERING or "price" in lower:
                return "Is price tampering validation performed in Loop 1 before payment execution in Loop 2?"
            return "When are security policy checks performed relative to payment execution in AgentGuard?"

        elif purpose == ConversationalPurpose.CLARIFICATION:
            return f"Explain {topic.value} conceptually without showing source code."

        # Pronoun replacement for live budget checks
        if "enough for" in lower or "can i buy" in lower or "sufficient to" in lower or "enough to" in lower:
            if "earbud" in lower or "earbuds" in lower:
                return "Is the current mandate budget sufficient to purchase Wireless Earbuds?"
            if "speaker" in lower:
                return "Is the current mandate budget sufficient to purchase Bluetooth Speaker?"
            return "Is the active mandate budget enough for the requested purchase?"

        return trimmed

    def _resolve_progressive_affirmation(
        self, offer: ProgressiveDisclosureOffer, session: ConversationSession
    ) -> ResponsePlan:
        """Constructs a ResponsePlan when user accepts a progressive disclosure offer."""
        if offer.offer_type == "CODE_IMPLEMENTATION":
            target = offer.target_symbol or offer.target_file or "the core policy engine"
            return ResponsePlan(
                intent=UserIntentCategory.CODE_REFERENCE,
                dialogue_act=DialogueAct.INFORM,
                resolved_query=f"Show code implementation details for {target}",
                needs_static_retrieval=True,
                needs_live_tool=False,
                progressive_stage="FOLLOWUP_ACCEPTED",
                suggested_action=offer.target_action,
            )
        elif offer.offer_type == "LIVE_STATE":
            return ResponsePlan(
                intent=UserIntentCategory.LIVE_DATA_QUERY,
                dialogue_act=DialogueAct.LIVE_STATUS,
                resolved_query="Inspect live runtime state",
                needs_static_retrieval=False,
                needs_live_tool=True,
                live_tool_request=LiveToolRequest(
                    tool_type=LiveToolType.MANDATE_BUDGET,
                    parameters={},
                    reason="User accepted live state inspection offer",
                ),
                progressive_stage="FOLLOWUP_ACCEPTED",
                suggested_action=offer.target_action,
            )
        elif offer.offer_type == "SCENARIO_SIMULATION":
            return ResponsePlan(
                intent=UserIntentCategory.SECURITY_SCENARIO,
                dialogue_act=DialogueAct.NAVIGATE,
                resolved_query="Simulate threat scenario in Threat Lab",
                needs_static_retrieval=True,
                needs_live_tool=False,
                progressive_stage="FOLLOWUP_ACCEPTED",
                suggested_action=offer.target_action,
            )
        else:
            return ResponsePlan(
                intent=UserIntentCategory.CONCEPT_EXPLANATION,
                dialogue_act=DialogueAct.INFORM,
                resolved_query="Explain deeper technical architecture",
                needs_static_retrieval=True,
                needs_live_tool=False,
                progressive_stage="FOLLOWUP_ACCEPTED",
            )

    def _check_live_routing(
        self, query: str, session: ConversationSession | None, raw_query: str = ""
    ) -> LiveToolRequest | None:
        """Deterministic check for live runtime state requirements."""
        texts = [query.lower()]
        if raw_query:
            texts.append(raw_query.lower())

        for pat, tool_type in self.LIVE_DATA_PATTERNS:
            for text in texts:
                if re.search(pat, text):
                    params: dict[str, Any] = {}
                    m_match = re.search(r"mandate-[0-9a-zA-Z_\-]+", text)
                    if m_match:
                        params["mandate_id"] = m_match.group(0)
                    elif session and "mandate_id" in session.active_entities:
                        params["mandate_id"] = session.active_entities["mandate_id"]
                    else:
                        params["mandate_id"] = "mandate-001"

                    t_match = re.search(r"txn-[0-9a-zA-Z_\-]+", text)
                    if t_match:
                        params["transaction_id"] = t_match.group(0)
                    elif session and "transaction_id" in session.active_entities:
                        params["transaction_id"] = session.active_entities["transaction_id"]

                    p_match = re.search(r"prod-[0-9a-zA-Z_\-]+", text)
                    if p_match:
                        params["product_id"] = p_match.group(0)
                    elif "earbud" in text:
                        params["product_id"] = "prod-001"
                    elif "speaker" in text:
                        params["product_id"] = "prod-002"
                    elif "charger" in text or "headphone" in text:
                        params["product_id"] = "prod-003"

                    return LiveToolRequest(
                        tool_type=tool_type,
                        parameters=params,
                        reason=f"Matched deterministic live pattern '{pat}'",
                    )
        return None

    def _map_resource_to_live_tool(self, resource: str) -> LiveToolType:
        if "mandate" in resource or "budget" in resource:
            return LiveToolType.MANDATE_BUDGET
        if "transaction" in resource:
            return LiveToolType.TRANSACTION_STATUS
        if "merchant" in resource:
            return LiveToolType.MERCHANT_CATALOG
        if "product" in resource or "stock" in resource:
            return LiveToolType.PRODUCT_CATALOG
        if "audit" in resource:
            return LiveToolType.AUDIT_CHAIN_INTEGRITY
        return LiveToolType.MANDATE_BUDGET

    def _map_classification_to_intent(
        self,
        classification: QueryClassification,
        raw_lower: str,
        resolved_query: str = "",
        purpose: ConversationalPurpose | None = None,
        canonical_topic: CanonicalTopic | None = None,
    ) -> tuple[UserIntentCategory, DialogueAct]:
        query_text = (resolved_query or raw_lower).lower()

        if purpose == ConversationalPurpose.PROJECT_WALKTHROUGH:
            return UserIntentCategory.PROJECT_WALKTHROUGH, DialogueAct.INFORM

        if purpose == ConversationalPurpose.CODE_LOCATION_REQUEST:
            return UserIntentCategory.CODE_REFERENCE, DialogueAct.INFORM

        if purpose == ConversationalPurpose.UI_NAVIGATION_REQUEST:
            return UserIntentCategory.FRONTEND_NAVIGATION, DialogueAct.NAVIGATE

        if purpose == ConversationalPurpose.EXAMPLE_REQUEST:
            if canonical_topic in (CanonicalTopic.PRICE_TAMPERING, CanonicalTopic.REPLAY_ATTACK):
                return UserIntentCategory.SECURITY_SCENARIO, DialogueAct.INFORM
            return UserIntentCategory.CONCEPT_EXPLANATION, DialogueAct.INFORM

        # Conceptual requests explicitly asking to exclude code
        if "without the code" in query_text or "without showing source code" in query_text or "without code" in query_text or "conceptually" in query_text:
            return UserIntentCategory.CONCEPT_EXPLANATION, DialogueAct.INFORM

        # Explicit overrides for code location / reference queries
        if any(w in raw_lower for w in [
            "where is", "where does that live", "where does it live", "where does that happen",
            "which file handles", "which module", "which file", "implemented in", "coded in",
            "source file", "where in the code", "point me to the code", "show me where that happens",
            "what's responsible for", "whats responsible for", "show code", "show me the code", "show the code",
        ]):
            return UserIntentCategory.CODE_REFERENCE, DialogueAct.INFORM

        # Explicit overrides for UI navigation
        if any(w in raw_lower for w in [
            "show me the relevant page", "which page", "which tab", "show me the page",
            "show me the forensic", "show me the transaction involved", "show me what happened",
            "where can i see", "take me to", "navigate to", "where in the ui", "where in the app",
            "relevant page",
        ]):
            return UserIntentCategory.FRONTEND_NAVIGATION, DialogueAct.NAVIGATE

        # Specific security attack scenarios
        if (
            purpose == ConversationalPurpose.COUNTERFACTUAL and canonical_topic in (CanonicalTopic.PRICE_TAMPERING, CanonicalTopic.REPLAY_ATTACK)
        ) or any(w in raw_lower for w in [
            "lies about the price", "lies about price", "price tampering", "fake price",
            "replay attack", "replay attacks", "budget exceeded", "over-budget", "over budget",
            "escalate", "attack scenario", "over budget proposal", "tamper",
        ]):
            # If asking overview/concept of audit chain, keep CONCEPT_EXPLANATION
            if "audit chain" in raw_lower or "how does the audit" in raw_lower:
                return UserIntentCategory.CONCEPT_EXPLANATION, DialogueAct.INFORM
            return UserIntentCategory.SECURITY_SCENARIO, DialogueAct.INFORM

        # Overview / Conceptual inquiries
        if any(w in raw_lower for w in [
            "tell me about the threat lab", "what is the threat lab", "what is threat lab",
            "how does the threat lab work", "what is agentguard", "why did you build",
            "why can't gemini", "why cant gemini", "explain how the firewall prevents",
            "explain how the firewall works", "how does dual-loop", "what are the 5 tabs",
            "tell me what this thing actually does", "what does agentguard do",
            "what is this thing", "what exactly is this thing", "never heard of it",
            "one-minute explanation", "one minute explanation", "elevator pitch",
            "explain to someone", "explain agentguard to someone", "tell me about the audit",
            "how does the audit chain work", "how does it protect against prompt injection",
        ]):
            return UserIntentCategory.CONCEPT_EXPLANATION, DialogueAct.INFORM

        cat = classification.category
        if cat == QueryCategory.CONCEPTUAL_PROJECT:
            if any(re.search(rf"\b{re.escape(w)}\b", raw_lower) for w in ["hello", "hi", "hey", "who are you", "what can you do"]):
                return UserIntentCategory.GREETING_OR_META, DialogueAct.INFORM
            return UserIntentCategory.CONCEPT_EXPLANATION, DialogueAct.INFORM
        elif cat == QueryCategory.SECURITY_SCENARIO:
            return UserIntentCategory.SECURITY_SCENARIO, DialogueAct.INFORM
        elif cat == QueryCategory.CODE_SYMBOL:
            return UserIntentCategory.CODE_REFERENCE, DialogueAct.INFORM
        elif cat == QueryCategory.FRONTEND_ACTION or cat == QueryCategory.API_ROUTE:
            if "page" in raw_lower or "tab" in raw_lower or "show me" in raw_lower or "where can i see" in raw_lower:
                return UserIntentCategory.FRONTEND_NAVIGATION, DialogueAct.NAVIGATE
            return UserIntentCategory.CODE_REFERENCE, DialogueAct.INFORM
        elif cat == QueryCategory.TEST_VERIFICATION:
            return UserIntentCategory.CODE_REFERENCE, DialogueAct.INFORM
        elif cat == QueryCategory.DYNAMIC_LIVE_DATA:
            return UserIntentCategory.LIVE_DATA_QUERY, DialogueAct.LIVE_STATUS
        else:
            return UserIntentCategory.CONCEPT_EXPLANATION, DialogueAct.INFORM

    def _detect_ui_action(
        self,
        query: str,
        intent: UserIntentCategory,
        canonical_topic: CanonicalTopic,
        session: ConversationSession | None = None,
    ) -> ConversationAction | None:
        lower = query.lower()

        # Project Walkthrough action recommendation
        if intent == UserIntentCategory.PROJECT_WALKTHROUGH or any(w in lower for w in ["walkthrough", "judge", "demo", "overview of what you've built", "show me around"]):
            return ConversationAction(
                action_type="NAVIGATE_TAB",
                ui_tab_target="COCKPIT",
                payload={
                    "surface_hint": "Project Walkthrough",
                    "recommended_path": ["COCKPIT", "DEFENSE", "THREAT", "FORENSICS", "TELEMETRY"],
                },
            )

        # Scenario Triggering
        if "scenario" in lower or "threat lab" in lower or "threat" in lower or "simulate" in lower or "run" in lower:
            if canonical_topic == CanonicalTopic.PRICE_TAMPERING or "price" in lower or "tamper" in lower:
                return ConversationAction(
                    action_type="TRIGGER_SCENARIO",
                    ui_tab_target="DEFENSE",
                    scenario_id=3,
                    payload={"scenario_name": "PRICE_TAMPERING"},
                )
            if canonical_topic == CanonicalTopic.REPLAY_ATTACK or "replay" in lower:
                return ConversationAction(
                    action_type="TRIGGER_SCENARIO",
                    ui_tab_target="DEFENSE",
                    scenario_id=4,
                    payload={"scenario_name": "REPLAY_ATTACK"},
                )
            if canonical_topic == CanonicalTopic.MANDATE_BUDGET or "budget" in lower or "over budget" in lower:
                return ConversationAction(
                    action_type="TRIGGER_SCENARIO",
                    ui_tab_target="DEFENSE",
                    scenario_id=2,
                    payload={"scenario_name": "OVER_BUDGET"},
                )
            if "threat" in lower or canonical_topic == CanonicalTopic.THREAT_LAB:
                return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="THREAT")

        # Multi-surface UI recommendation inquiry
        if any(w in lower for w in ["navigation recommendations", "action hints", "ui recommendations", "surfaces", "surface recommendations"]):
            return ConversationAction(
                action_type="NAVIGATE_TAB",
                ui_tab_target="FORENSICS",
                payload={
                    "surface_hint": "Forensic Ledger",
                    "available_surfaces": ["Forensic Ledger", "Threat Lab", "Live Protection"],
                },
            )

        # Forensic Audit Ledger
        if (
            "audit" in lower
            or "ledger" in lower
            or "forensic" in lower
            or "transaction involved" in lower
            or canonical_topic in (CanonicalTopic.AUDIT_CHAIN, CanonicalTopic.FORENSIC_LEDGER)
        ):
            return ConversationAction(
                action_type="NAVIGATE_TAB",
                ui_tab_target="FORENSICS",
                payload={"surface_hint": "Forensic Ledger"},
            )

        # Defense / Decision Trace / Live Protection
        if "show me what happened" in lower or "defense" in lower or "firewall" in lower or "decision" in lower or "trace" in lower or "live protection" in lower:
            return ConversationAction(
                action_type="NAVIGATE_TAB",
                ui_tab_target="DEFENSE",
                payload={"surface_hint": "Live Protection"},
            )

        if "cockpit" in lower or "overview" in lower:
            return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="COCKPIT")

        if any(w in lower for w in ["page", "pages", "tab", "tabs", "screen", "screens", "where in the ui", "where in the app", "relevant page"]):
            if canonical_topic == CanonicalTopic.PRICE_TAMPERING or "tamper" in lower or "attack" in lower or "firewall" in lower or "defense" in lower:
                return ConversationAction(
                    action_type="NAVIGATE_TAB",
                    ui_tab_target="DEFENSE",
                    payload={"surface_hint": "Live Protection"},
                )
            if canonical_topic in (CanonicalTopic.AUDIT_CHAIN, CanonicalTopic.FORENSIC_LEDGER) or "audit" in lower:
                return ConversationAction(
                    action_type="NAVIGATE_TAB",
                    ui_tab_target="FORENSICS",
                    payload={"surface_hint": "Forensic Ledger"},
                )
            if canonical_topic == CanonicalTopic.THREAT_LAB or "threat" in lower:
                return ConversationAction(
                    action_type="NAVIGATE_TAB",
                    ui_tab_target="THREAT",
                    payload={"surface_hint": "Threat Lab"},
                )
            return ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="COCKPIT")

        return None



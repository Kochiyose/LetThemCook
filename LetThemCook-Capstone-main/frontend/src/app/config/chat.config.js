// =============================================================================
// This file controls everything that appears inside the AI chat panel.
//
// HOW TO EDIT:
//   - Change any string value between the quotes " "
//   - Do NOT change the variable names (WELCOME_MESSAGE, AI_FALLBACK_REPLIES…)
//     because App.js imports them by name
// =============================================================================


// This is the first message users see when they open the chat
export const WELCOME_MESSAGE =
  "Hi there! 🧑‍🍳 I'm Chef Logro, your sweet and caring culinary assistant. Tell me what ingredients you have on hand, and I'll help you find the perfect recipe. You can also ask me about cooking tips, substitutions, or how to store food!";


// These messages cycle in order - one per user message
// BACKEND: Once your Ollama endpoint is ready, replace this with real AI responses
export const AI_FALLBACK_REPLIES = [
  "Great choice! With those ingredients, you're already most of the way there. The key is to start with the recipe that uses your most perishable items first — that's how you reduce waste and save money.",
  "Good question! If you're out of butter, neutral oil (like vegetable or canola) works at about 75% of the quantity — since oil is 100% fat while butter has some water content, the texture differs slightly but the flavour holds up well.",
  "That's the smart approach! Always cook the most perishable ingredients first — fresh proteins and vegetables before pantry staples. The ranking system is designed exactly around this logic.",
  "A recipe ranks lower when it needs ingredients you don't currently have. But here's the good news — the available-ingredients-only recipes above it are just as delicious and ready to cook right now!",
  "Pro tip for storing herbs: wrap them in a slightly damp paper towel, place in a zip-lock bag, and refrigerate. They'll last 1–2 weeks this way. Hard cheeses freeze beautifully. Onions and garlic prefer a cool, dry, dark spot.",
  "You can absolutely scale recipes proportionally. If you only have half the protein a recipe calls for, halve the aromatics and fat too — this keeps the flavour balance right and prevents the dish from tasting off.",
  "I’ll keep recipe suggestions practical and focused on the ingredients you have available.",
];


// These are shortcut buttons displayed above the chat input
export const QUICK_PROMPTS = [
  "What can I make with eggs and butter?",
  "How do I store leftover herbs?",
  "Can I substitute oil for butter?",
];


// Settings for the chat panel header
export const CHAT_HEADER = {
  name: "Chef Logro",
  statusIdle: "Llama 3.2 · Local",
  statusThinking: "Thinking…",
};


// Small hint text below the chat input
export const CHAT_INPUT_HINT = "Enter to send · Shift+Enter for new line";

// Placeholder text inside the chat textarea
export const CHAT_INPUT_PLACEHOLDER =
  "Type your ingredients or ask a cooking question…";

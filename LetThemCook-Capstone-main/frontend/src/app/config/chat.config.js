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
  "Hi there! 🧑‍🍳 I'm KitchenAI, your sweet and caring culinary assistant. Tell me what ingredients you have on hand, and I'll help you find the perfect recipe. You can also ask me about cooking tips, substitutions, or how to store food!";


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


// These are shortcut buttons displayed above the chat input.
// A random handful is picked from this pool each time (see QUICK_PROMPT_COUNT
// below), so the buttons don't look the same every visit. Keep these focused
// on finding/choosing a recipe — general cooking-tip questions live in
// PANTRY_QUICK_PROMPTS / RECIPE_QUICK_PROMPTS instead, which are more useful
// since they reference the user's actual pantry or open recipe.
export const QUICK_PROMPTS = [
  "What can I make with eggs and butter?",
  "What recipe can I make right now?",
  "Suggest a recipe using what's in my pantry.",
  "What's the easiest recipe here to start with?",
  "Recommend a quick recipe for tonight.",
  "What recipe uses the fewest ingredients?",
  "Suggest a recipe for a beginner cook.",
  "What's a good recipe if I only have 20 minutes?",
  "Recommend a recipe using my most perishable ingredients.",
  "What recipe should I try that's a bit different?",
  "Suggest a healthy recipe I can make today.",
  "What recipe pairs well with what I already have?",
  "Recommend a recipe that uses up my leftovers.",
];

// Use {ingredient} as a placeholder — it will be swapped for a random item
// currently in the user's pantry, so the suggestion changes as their pantry
// changes. These are mixed in with QUICK_PROMPTS above whenever the pantry
// isn't empty.
export const PANTRY_QUICK_PROMPTS = [
  "What recipe can I make with {ingredient}?",
  "Suggest a recipe that uses up my {ingredient}.",
  "What recipe pairs well with {ingredient}?",
  "Any recipe ideas built around {ingredient}?",
];

// Use {recipe} as a placeholder — it will be swapped for the name of the
// recipe the user currently has open, so the suggestion changes with
// whichever recipe they're looking at. Mixed in whenever a recipe is open.
export const RECIPE_QUICK_PROMPTS = [
  "Can I substitute an ingredient in {recipe}?",
  "How do I scale {recipe} up or down?",
  "What's a good side dish to serve with {recipe}?",
  "Any tips for making {recipe} turn out well?",
  "How should I store leftovers from {recipe}?",
];

// How many quick-prompt buttons to show at once.
export const QUICK_PROMPT_COUNT = 3;


// Settings for the chat panel header
export const CHAT_HEADER = {
  name: "KitchenAI",
  statusIdle: "Llama 3.2 · Local",
  statusThinking: "Thinking…",
};


// Small hint text below the chat input
export const CHAT_INPUT_HINT = "Enter to send · Shift+Enter for new line";

// Placeholder text inside the chat textarea
export const CHAT_INPUT_PLACEHOLDER =
  "Type your ingredients or ask a cooking question…";
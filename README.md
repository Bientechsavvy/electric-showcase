# Electric Showcase + Local AI Intake Assistant

Built for a friend who runs a small electrical services business.

- `index.html`: public showcase page. Customers send a request straight to WhatsApp.
- `intake.py`: owner-only assistant. Runs an open-weight model locally with Ollama and turns messy customer messages into a clean job summary, urgency level, follow-up questions and a draft reply.

## Run it
1. Install Ollama from ollama.com, then: `ollama pull llama3.2:3b`
2. `python intake.py` and paste a customer message.
3. Try another model: `MODEL=qwen2.5:3b python intake.py`
4. Open `index.html` in a browser. Put job photos in a `jobs/` folder named `job1.jpg` to `job6.jpg`.
5. Edit `YOUR BUSINESS NAME`, `YOUR PHONE NUMBER` and `PHONE_NUMBER_WITH_COUNTRY_CODE` (digits only).

## Why open source
- Runs on a laptop, works offline.
- Customer names, addresses and phone numbers stay on the owner's computer.
- Free to run, no per-message API cost.
- Prompt and model can be changed to fit the business.

## Safety
The assistant never invents prices or gives repair instructions. A keyword check runs before the model and flags fire or shock risks.
## Live link : https://bientechsavvy.github.io/electric-showcase/

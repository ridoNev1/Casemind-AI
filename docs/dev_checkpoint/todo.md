# Development TODO

Terakhir diperbarui: 7 Nov 2025  
PIC: Rido Maulana (user)

---

## Backlog Inti (Hackathon Scope)
- Finalize agentic AI copilot workflow (LLM summary + chat history + feedback loop) sesuai requirement hackathon dan siapkan demo script (curl + penjelasan flow auditor → copilot → feedback). Deliverable: endpoint `GET/POST /claims/{id}/chat`, integrasi `langchain-openai`, FE chat panel, serta narasi demo (lihat `docs/dev_checkpoint/chat_copilot_workflow.md`).
- ✅ Rancang rencana pemanfaatan feedback auditor: definisikan struktur dataset monitoring & outline eksperimen supervised (lihat `docs/dev_checkpoint/feedback_utilization_plan.md`).

---

## Nice to Have / Post-Hackathon

### Data Governance & Integrasi
- Lengkapi hashing/anonymisation pipeline bila ada sumber data tambahan agar PII tetap terlindungi saat pipeline diperluas.

### Copilot & Pembelajaran
- (dipindah ke Backlog Inti)

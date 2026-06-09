# RootEd LangGraph Migration TODO

## Phase 1: Foundation & Dependencies ✅
- [x] Add `langgraph` to `requirements.txt`
- [x] Install new dependencies

## Phase 2: Core Logic Rewrite (`logic.py`) ✅
- [x] Remove legacy regex extraction logic
- [x] Define LangGraph `MessagesState`
- [x] Implement `plot_graph` tool with `@tool` decorator
- [x] Implement `call_model` node (LLM interaction)
- [x] Implement `call_tool` node (Graphing execution)
- [x] Compile the `StateGraph`

## Phase 3: API Integration (`api.py`) ✅
- [x] Refactor `api.py` to use LangGraph app
- [x] Implement history conversion from Supabase to LangChain messages
- [x] Update `/api/chat` endpoint to extract responses from graph state

## Phase 4: Verification 🕒
- [ ] Verify text-only responses
- [ ] Verify integral graphing (No regex)
- [ ] Verify parametric graphing (No regex)
- [ ] Final UI/UX check

.PHONY: install assess run demo clean

install:
	pip install -r requirements.txt

assess:
	@if [ -z "$$ANTHROPIC_API_KEY" ]; then \
		echo "ANTHROPIC_API_KEY not set. Activate per CLAUDE.md."; exit 1; \
	fi
	python -m app.engine

run:
	streamlit run app/streamlit_app.py

demo: install assess run

clean:
	rm -rf outputs/assessments/*.json

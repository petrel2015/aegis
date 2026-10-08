# Fictional release record — not an actual deployment

- run_id: 123456781234123412341234567890ab
- execution_mode: external
- authorization_ref: User explicitly requested publishing to example/taskboard-pages.
- source: example/taskboard, aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
- artifact: example/taskboard-pages, bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
- artifact_digest: sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
- build: npm run build:pages; Node 22; pages mode; /taskboard-pages/ base path
- site_url: https://example.github.io/taskboard-pages/
- deployment: pending; no observed public version or browser proof yet
- rollback: deploy the previous retained artifact through the same project procedure

The build was checked locally. This report does not claim publication, public accessibility,
or an AEGIS review chain. A later receipt must link the actual deployment, compare live files
and record a successful public smoke test before using status=verified.

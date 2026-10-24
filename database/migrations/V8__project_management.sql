ALTER TABLE projects
  ADD COLUMN deleted_at DATETIME(6) NULL,
  ADD COLUMN content_version INT NOT NULL DEFAULT 1,
  ADD CONSTRAINT ck_project_content_version CHECK (content_version > 0),
  ADD KEY ix_projects_active (deleted_at, created_at, id);

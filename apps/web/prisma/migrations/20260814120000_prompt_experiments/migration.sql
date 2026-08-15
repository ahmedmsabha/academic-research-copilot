-- CreateTable
CREATE TABLE "prompt_experiments" (
    "id" TEXT NOT NULL,
    "run_id" TEXT NOT NULL,
    "project_id" TEXT NOT NULL,
    "owner_user_id" TEXT NOT NULL,
    "user_input" TEXT NOT NULL,
    "strategy" TEXT NOT NULL,
    "template_version" TEXT NOT NULL,
    "model" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "generated_output" TEXT NOT NULL,
    "elapsed_ms" INTEGER NOT NULL,
    "prompt_tokens" INTEGER,
    "completion_tokens" INTEGER,
    "total_tokens" INTEGER,
    "rating_accuracy" INTEGER,
    "rating_clarity" INTEGER,
    "rating_research_usefulness" INTEGER,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "prompt_experiments_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "prompt_experiments_project_id_created_at_idx" ON "prompt_experiments"("project_id", "created_at");

-- CreateIndex
CREATE INDEX "prompt_experiments_owner_user_id_idx" ON "prompt_experiments"("owner_user_id");

-- CreateIndex
CREATE INDEX "prompt_experiments_run_id_idx" ON "prompt_experiments"("run_id");

-- AddForeignKey
ALTER TABLE "prompt_experiments" ADD CONSTRAINT "prompt_experiments_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE CASCADE;

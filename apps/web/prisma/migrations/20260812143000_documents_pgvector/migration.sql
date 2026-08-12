-- CreateExtension
CREATE EXTENSION IF NOT EXISTS vector;

-- AlterTable
ALTER TABLE "messages" ADD COLUMN "citations_json" TEXT;

-- CreateTable
CREATE TABLE "documents" (
    "id" TEXT NOT NULL,
    "project_id" TEXT NOT NULL,
    "owner_user_id" TEXT NOT NULL,
    "filename" TEXT NOT NULL,
    "content_type" TEXT NOT NULL,
    "size_bytes" INTEGER NOT NULL,
    "checksum" TEXT,
    "storage_key" TEXT NOT NULL,
    "page_count" INTEGER,
    "status" TEXT NOT NULL DEFAULT 'uploaded',
    "failure_code" TEXT,
    "failure_message" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "documents_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "document_chunks" (
    "id" TEXT NOT NULL,
    "project_id" TEXT NOT NULL,
    "document_id" TEXT NOT NULL,
    "ordinal" INTEGER NOT NULL,
    "content" TEXT NOT NULL,
    "page_start" INTEGER,
    "page_end" INTEGER,
    "char_start" INTEGER,
    "char_end" INTEGER,
    "embedding_model" TEXT NOT NULL,
    "embedding_dimension" INTEGER NOT NULL,
    "embedding" vector(768),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "document_chunks_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "documents_project_id_status_idx" ON "documents"("project_id", "status");

-- CreateIndex
CREATE INDEX "documents_owner_user_id_idx" ON "documents"("owner_user_id");

-- CreateIndex
CREATE INDEX "document_chunks_project_id_document_id_idx" ON "document_chunks"("project_id", "document_id");

-- CreateIndex
CREATE UNIQUE INDEX "document_chunks_document_id_ordinal_key" ON "document_chunks"("document_id", "ordinal");

-- AddForeignKey
ALTER TABLE "documents" ADD CONSTRAINT "documents_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "document_chunks" ADD CONSTRAINT "document_chunks_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE CASCADE ON UPDATE CASCADE;

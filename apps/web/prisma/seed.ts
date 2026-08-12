import "dotenv/config";
import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "../generated/prisma/client";

const connectionString = process.env.DATABASE_URL;
if (!connectionString) {
  throw new Error("DATABASE_URL is not set.");
}

const prisma = new PrismaClient({
  adapter: new PrismaPg({ connectionString }),
});

async function main() {
  const alice = await prisma.user.upsert({
    where: { email: "alice@example.com" },
    update: {},
    create: {
      email: "alice@example.com",
      name: "Alice",
      posts: {
        create: [
          {
            title: "Getting started with research notes",
            content: "Capture questions before you open the PDF.",
            published: true,
          },
          {
            title: "Draft citation checklist",
            content: "Filename and page number for every claim.",
            published: false,
          },
        ],
      },
    },
  });

  const bob = await prisma.user.upsert({
    where: { email: "bob@example.com" },
    update: {},
    create: {
      email: "bob@example.com",
      name: "Bob",
      posts: {
        create: [
          {
            title: "Why grounded answers matter",
            content: "Never invent a source page.",
            published: true,
          },
        ],
      },
    },
  });

  console.log(`Seeded users: ${alice.email}, ${bob.email}`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

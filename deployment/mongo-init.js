// MongoDB initialization script for production
// This script runs when the MongoDB container first starts

// Switch to the AARIS database
db = db.getSiblingDB('aaris');

// Create collections with validation
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['email', 'password', 'role', 'created_at'],
      properties: {
        email: {
          bsonType: 'string',
          pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        },
        role: {
          enum: ['author', 'reviewer', 'editor', 'admin', 'super_admin']
        },
        is_active: {
          bsonType: 'bool'
        }
      }
    }
  }
});

db.createCollection('submissions', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['title', 'content', 'status', 'created_at'],
      properties: {
        status: {
          enum: ['pending', 'running', 'completed', 'failed']
        }
      }
    }
  }
});

db.createCollection('agent_tasks');
db.createCollection('audit_logs');
db.createCollection('api_keys');
db.createCollection('passkeys');
db.createCollection('totp_secrets');
db.createCollection('otp_codes');
db.createCollection('reviews');
db.createCollection('document_embeddings');
db.createCollection('workflow_checkpoints');
db.createCollection('embedding_cache');

// Create indexes for performance
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ role: 1 });
db.users.createIndex({ created_at: -1 });

db.submissions.createIndex({ user_id: 1 });
db.submissions.createIndex({ status: 1 });
db.submissions.createIndex({ created_at: -1 });
db.submissions.createIndex({ detected_domain: 1 });

db.agent_tasks.createIndex({ submission_id: 1 });
db.agent_tasks.createIndex({ agent_type: 1 });
db.agent_tasks.createIndex({ status: 1 });

db.audit_logs.createIndex({ user_id: 1 });
db.audit_logs.createIndex({ action: 1 });
db.audit_logs.createIndex({ timestamp: -1 });
db.audit_logs.createIndex({ ip_address: 1 });

db.api_keys.createIndex({ user_id: 1 });
db.api_keys.createIndex({ key_hash: 1 }, { unique: true });
db.api_keys.createIndex({ expires_at: 1 });

db.passkeys.createIndex({ user_id: 1 });
db.passkeys.createIndex({ credential_id: 1 }, { unique: true });

db.totp_secrets.createIndex({ user_id: 1 }, { unique: true });

db.otp_codes.createIndex({ email: 1 });
db.otp_codes.createIndex({ expires_at: 1 });

db.reviews.createIndex({ submission_id: 1 });
db.reviews.createIndex({ reviewer_id: 1 });
db.reviews.createIndex({ status: 1 });
db.reviews.createIndex({ created_at: -1 });

db.document_embeddings.createIndex({ submission_id: 1 });
db.document_embeddings.createIndex({ created_at: -1 });
db.document_embeddings.createIndex({ user_id: 1 });

db.workflow_checkpoints.createIndex({ submission_id: 1 }, { unique: true });
db.workflow_checkpoints.createIndex({ created_at: -1 });

db.embedding_cache.createIndex({ content_hash: 1 }, { unique: true });
db.embedding_cache.createIndex({ created_at: 1 }, { expireAfterSeconds: 2592000 }); // 30 days TTL

// Create vector search index for RAG (Atlas only)
// Note: Vector search indexes must be created via Atlas UI or API
// This is a placeholder for documentation
// Index name: vector_index
// Field: embedding
// Dimensions: 1536 (OpenAI ada-002)
// Similarity: cosine

// Create TTL indexes for automatic cleanup
db.otp_codes.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });
db.audit_logs.createIndex({ timestamp: 1 }, { expireAfterSeconds: 7776000 }); // 90 days

print('MongoDB initialization completed successfully');

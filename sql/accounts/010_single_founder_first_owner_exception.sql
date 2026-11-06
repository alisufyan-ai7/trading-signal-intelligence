-- Owner-authorized narrow initial-founder exception, 2026-11-06.
-- Apply ONCE under vowsig_migrator to STAGING first, with reviewed SQL.
-- 009 two-person approvals remain REQUIRED for normal first_owner and
-- rotate_factor. Solo never permits recovery or a second owner.
-- Signed one-use approval, exact immutable Auth0 binding, TOTP confirmation,
-- schema migrator and session revocation are still enforced in Python.
BEGIN;
SET LOCAL search_path TO vowsig, pg_catalog;
DO $$
BEGIN
    IF current_user <> 'vowsig_migrator' THEN
        RAISE EXCEPTION 'Dedicated migrator required';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema='vowsig'
        AND table_name='vowsig_owner_provisioning_audit'
        AND constraint_name='vowsig_owner_independent_review'
    ) THEN
        RAISE EXCEPTION 'Existing two-person policy constraint absent';
    END IF;
END $$;

ALTER TABLE vowsig_owner_provisioning_audit
    DROP CONSTRAINT vowsig_owner_independent_review;

ALTER TABLE vowsig_owner_provisioning_audit
    DROP CONSTRAINT vowsig_owner_provisioning_audit_operation_check;

ALTER TABLE vowsig_owner_provisioning_audit
    ADD CONSTRAINT vowsig_owner_operation_scope_check CHECK (
        operation IN ('first_owner','first_owner_solo','rotate_factor')
    );

ALTER TABLE vowsig_owner_provisioning_audit
    ADD CONSTRAINT vowsig_owner_actor_policy_check CHECK (
        (
            operation='first_owner_solo'
            AND operator_id=reviewer_id
        )
        OR (
            operation IN ('first_owner','rotate_factor')
            AND operator_id<>reviewer_id
        )
    );

-- No new role grants, runtime DML or HTTP paths.
COMMIT;

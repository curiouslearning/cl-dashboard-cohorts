-- =====================================================================================
  -- Nightly sticky cohort upsert (multi-cohort + derived app cohorts)
  --
  -- Table: dataexploration-193817.user_data.cr_cohorts
  -- Schema: (cr_user_id STRING/INT64, cohort_name STRING)
  --
  -- Behavior:
  -- - Sticky: inserts new (cr_user_id, cohort_name) pairs; never removes existing rows
  -- - Deterministic user base: picks exactly 1 row per cr_user_id (highest max_user_level, then latest last_event_date)
  -- - Program cohorts: add/edit definitions in cohort_rules below (prefixed "program:")
  -- - App cohorts: for any user with app != 'CR', inserts cohort_name = CONCAT('app:', app)
  -- - MERGE prevents duplicates for (cr_user_id, cohort_name)
  --
  -- Guidance: avoid defining a program rule that only filters on `apps` for a single
  -- non-CR app — the `app:<name>` derived cohort already covers that exact population
  -- and you'll get duplicate dropdown entries with identical user sets.
  -- =====================================================================================

  MERGE `dataexploration-193817.user_data.cr_cohorts` AS tgt
  USING (
    WITH base_users AS (
      SELECT
        cr_user_id,
        first_open,
        country,
        app_language,
        app,
        max_user_level,
        last_event_date
      FROM `dataexploration-193817.user_data.cr_user_progress`
      WHERE cr_user_id IS NOT NULL
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY cr_user_id
        ORDER BY max_user_level DESC, last_event_date DESC
      ) = 1
    ),

    -- -------------------------------------------------------------------------------
    -- Cohort definitions (add more STRUCT rows)
    -- Conventions:
    -- - Use prefixes to avoid collisions: "program:" and "app:"
    -- - NULL means "no filter" for that field
    -- -------------------------------------------------------------------------------
    cohort_rules AS (
      SELECT * FROM UNNEST([
        STRUCT(
          'program:Congo - Brazzaville' AS cohort_name,
          DATE '2026-01-18'             AS first_open_after,
          ['Congo - Brazzaville']       AS countries,
          ['french','english']          AS languages,
          ['CR']                        AS apps
        )
  
        -- Example with no language filter:
        -- ,STRUCT(
        --   'program:Global CR since Feb' AS cohort_name,
        --   DATE '2026-02-01'             AS first_open_after,
        --   NULL                          AS countries,
        --   NULL                          AS languages,
        --   ['CR']                        AS apps
        -- )
      ])
    ),

    -- Program cohort memberships
    rule_memberships AS (
      SELECT
        u.cr_user_id,
        r.cohort_name
      FROM base_users u
      JOIN cohort_rules r
        ON (r.first_open_after IS NULL OR u.first_open > r.first_open_after)
       AND (r.countries       IS NULL OR u.country      IN UNNEST(r.countries))
       AND (r.languages       IS NULL OR u.app_language IN UNNEST(r.languages))
       AND (r.apps            IS NULL OR u.app          IN UNNEST(r.apps))
    ),

    -- Derived app cohorts (any non-CR app)
    app_memberships AS (
      SELECT
        cr_user_id,
        CONCAT('app:', app) AS cohort_name
      FROM base_users
      WHERE app IS NOT NULL
        AND app != 'CR'
    ),
  
    -- Final source set
    src AS (
      SELECT DISTINCT cr_user_id, cohort_name
      FROM (
        SELECT cr_user_id, cohort_name FROM rule_memberships
        UNION ALL
        SELECT cr_user_id, cohort_name FROM app_memberships
      )
    )

    SELECT * FROM src
  ) AS src
  ON tgt.cr_user_id = src.cr_user_id
  AND tgt.cohort_name = src.cohort_name
  WHEN NOT MATCHED THEN
    INSERT (cr_user_id, cohort_name)
    VALUES (src.cr_user_id, src.cohort_name);


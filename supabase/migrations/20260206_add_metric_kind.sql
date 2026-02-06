-- Add metric kind metadata (additive, backwards compatible)
alter table metrics
  add column if not exists metric_kind text,
  add column if not exists higher_is_better boolean default true;

alter table metrics
  drop constraint if exists metrics_kind_check;
alter table metrics
  add constraint metrics_kind_check
  check (metric_kind in ('quantitative', 'count', 'score') or metric_kind is null);

-- For now, keep kind consistent with existing unit_type to avoid ambiguous behavior.
alter table metrics
  drop constraint if exists metrics_kind_unit_type_consistency;
alter table metrics
  add constraint metrics_kind_unit_type_consistency
  check (
    metric_kind is null
    or (metric_kind = 'quantitative' and unit_type = 'float')
    or (metric_kind = 'count' and unit_type = 'integer')
    or (metric_kind = 'score' and unit_type = 'integer_range')
  );

SELECT base.filename, base.checksum__min AS checksum, base.annotations__count AS annotation_count, {% for location in locations %} l{{ location.pk }}.checksum AS l{{ location.pk }}c{% if not forloop.last %},{% endif %}{% endfor %}
FROM
  (
    -- SELECT filename, MIN(checksum) as checksum
    -- FROM inventory_record
    -- --WHERE inventory_record.location_id IN (5, 6, 8)
    -- -- TODO: MD filters here
    -- GROUP BY filename
    {{ base_query|safe }}
  ) AS base
{% for location in locations %}
LEFT JOIN
  (
    SELECT filename, checksum
    FROM inventory_record
    WHERE inventory_record.location_id = {{ location.pk }}
  ) AS l{{ location.pk }}
ON base.filename = l{{ location.pk }}.filename{% endfor %}
WHERE{% for location in locations %}
{% if not forloop.first %}OR {% endif %}l{{ location.pk }}.checksum IS NULL OR l{{ location.pk }}.checksum != base.checksum__min{% endfor %};

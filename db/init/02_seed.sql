-- Seed publishers (UUIDs)
INSERT INTO publishers (publisher_id, publisher_name) VALUES
  ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Acme Ads'),
  ('b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'BrightMedia'),
  ('e4ccde33-df4f-8c3c-ff01-0ffdf17c4e55', 'ClickCorp')
ON CONFLICT DO NOTHING;

-- Seed campaigns
INSERT INTO campaigns (campaign_id, publisher_id, start_date) VALUES
  ('c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', '2026-01-01 00:00:00+00'),
  ('d3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', '2026-01-01 00:00:00+00'),
  ('f5ddff44-e050-9d4d-0012-100e028d5f66', 'e4ccde33-df4f-8c3c-ff01-0ffdf17c4e55', '2026-01-01 00:00:00+00')
ON CONFLICT DO NOTHING;

-- Seed raw_metrics (hourly buckets for 2026-01-01, publisher 1)
INSERT INTO raw_metrics (bucket_timestamp, publisher_id, campaign_id, impression_count, click_count, conversion_count) VALUES
  ('2026-01-01 00:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 120, 8, 2),
  ('2026-01-01 01:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 135, 9, 3),
  ('2026-01-01 02:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 110, 10, 1),
  ('2026-01-01 03:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 98,  8, 2),
  ('2026-01-01 04:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 102, 9, 1),
  ('2026-01-01 05:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 88,  7, 1),
  ('2026-01-01 06:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 145, 10, 4),
  ('2026-01-01 07:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 160, 10, 3),
  ('2026-01-01 08:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 175, 7, 2),
  ('2026-01-01 09:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 190, 10, 5),
  ('2026-01-01 10:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 210, 12, 4),
  ('2026-01-01 11:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 225, 14, 6),
  ('2026-01-01 12:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 240, 15, 5),
  ('2026-01-01 13:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 230, 13, 4),
  ('2026-01-01 14:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 220, 11, 3),
  ('2026-01-01 15:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 200, 10, 3),
  ('2026-01-01 16:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 185, 9, 2),
  ('2026-01-01 17:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 170, 8, 2),
  ('2026-01-01 18:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 155, 9, 3),
  ('2026-01-01 19:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 140, 8, 2),
  ('2026-01-01 20:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 130, 7, 1),
  ('2026-01-01 21:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 115, 6, 1),
  ('2026-01-01 22:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 105, 5, 1),
  ('2026-01-01 23:00:00+00', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'c2aade11-be2d-6a1a-dd8f-8ddbdf5a2c33', 95,  4, 0)
ON CONFLICT DO NOTHING;

-- Seed raw_metrics (hourly buckets for 2026-01-01, publisher 2)
INSERT INTO raw_metrics (bucket_timestamp, publisher_id, campaign_id, impression_count, click_count, conversion_count) VALUES
  ('2026-01-01 00:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 80,  5, 1),
  ('2026-01-01 01:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 75,  4, 1),
  ('2026-01-01 02:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 60,  3, 0),
  ('2026-01-01 03:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 55,  3, 0),
  ('2026-01-01 04:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 50,  2, 0),
  ('2026-01-01 05:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 48,  2, 0),
  ('2026-01-01 06:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 90,  6, 2),
  ('2026-01-01 07:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 110, 7, 2),
  ('2026-01-01 08:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 130, 8, 3),
  ('2026-01-01 09:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 150, 9, 3),
  ('2026-01-01 10:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 165, 10, 4),
  ('2026-01-01 11:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 180, 12, 5),
  ('2026-01-01 12:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 175, 11, 4),
  ('2026-01-01 13:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 170, 10, 3),
  ('2026-01-01 14:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 160, 9, 3),
  ('2026-01-01 15:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 145, 8, 2),
  ('2026-01-01 16:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 130, 7, 2),
  ('2026-01-01 17:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 120, 6, 1),
  ('2026-01-01 18:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 110, 6, 1),
  ('2026-01-01 19:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 100, 5, 1),
  ('2026-01-01 20:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 90,  4, 1),
  ('2026-01-01 21:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 85,  4, 0),
  ('2026-01-01 22:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 70,  3, 0),
  ('2026-01-01 23:00:00+00', 'b1ffcd00-ad1c-5f09-cc7e-7ccace491b22', 'd3bbef22-cf3e-7b2b-ee90-9eece06b3d44', 65,  3, 0)
ON CONFLICT DO NOTHING;

from datetime import datetime, timedelta
from app.db.supabase_client import get_supabase_client

class SecurityAuditService:
    """Service for security auditing and compliance"""
    
    @staticmethod
    def get_recent_events(event_type=None, user_id=None, hours=24, limit=100):
        """Get recent audit events"""
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        client = get_supabase_client()
        q = client.table('audit_logs').select('*').gte('timestamp', cutoff_time).order('timestamp', desc=True)
        if event_type:
            q = q.eq('event_type', event_type)
        if user_id:
            q = q.eq('user_id', user_id)
        resp = q.limit(limit).execute()
        return getattr(resp, 'data', []) or []
    
    @staticmethod
    def get_failed_login_attempts(username=None, hours=24):
        """Get failed login attempts"""
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        client = get_supabase_client()
        # Supabase returns count reliably when head=True is used.
        q = (
            client.table('audit_logs')
            .select('id', count='exact', head=True)
            .eq('event_type', 'login')
            .eq('status', 'failure')
            .gte('timestamp', cutoff_time)
        )
        if username:
            q = q.eq('username', username)
        resp = q.execute()
        return getattr(resp, 'count', 0) or 0
    
    @staticmethod
    def get_config_changes(config_id=None, hours=24):
        """Get configuration data changes"""
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        client = get_supabase_client()
        q = client.table('audit_logs').select('*').in_('event_type', ['config_create', 'config_update', 'config_delete']).gte('timestamp', cutoff_time).order('timestamp', desc=True)
        if config_id:
            q = q.eq('resource_id', config_id)
        resp = q.execute()
        return getattr(resp, 'data', []) or []
    
    @staticmethod
    def generate_security_report(hours=24):
        """Generate security report for compliance"""
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
        client = get_supabase_client()
        def count_query(filters):
            q = client.table('audit_logs').select('id', count='exact', head=True).gte('timestamp', cutoff_time)
            for key, value in filters.items():
                if key == 'event_type_in':
                    q = q.in_('event_type', value)
                else:
                    q = q.eq(key, value)
            resp = q.execute()
            return getattr(resp, 'count', 0) or 0
        total_events = count_query({})
        failed_logins = count_query({'event_type': 'login', 'status': 'failure'})
        config_changes = count_query({'event_type_in': ['config_create', 'config_update', 'config_delete']})
        critical_events = count_query({'severity': 'critical'})
        # Unique users: fetch user_ids and count unique
        resp_users = client.table('audit_logs').select('user_id').neq('user_id', None).gte('timestamp', cutoff_time).execute()
        user_ids = [row.get('user_id') for row in (getattr(resp_users, 'data', []) or []) if row.get('user_id') is not None]
        unique_users = len(set(user_ids))
        return {
            'period_hours': hours,
            'total_events': total_events,
            'failed_logins': failed_logins,
            'config_changes': config_changes,
            'critical_events': critical_events,
            'unique_users': unique_users,
            'generated_at': datetime.utcnow().isoformat()
        }


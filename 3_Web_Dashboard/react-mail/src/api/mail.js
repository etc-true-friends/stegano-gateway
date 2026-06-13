export const mockMessages = [
  {
    id: 'msg-001',
    sender: 'security-gateway@local',
    subject: 'Attachment scan completed',
    preview: 'The uploaded image was sanitized and delivered safely.',
    time: '09:24',
    verdict: 'CLEAN',
    body: 'Your attachment passed MIME validation, AI analysis, and CDR reconstruction. The sanitized copy is available in this mailbox.',
  },
  {
    id: 'msg-002',
    sender: 'partner@example.com',
    subject: 'Quarterly report images',
    preview: 'Please review the attached chart images before the meeting.',
    time: '08:51',
    verdict: 'CLEAN',
    body: 'The gateway received several report images from an external partner. This placeholder view is ready for API integration.',
  },
  {
    id: 'msg-003',
    sender: 'gateway-alert@local',
    subject: 'Suspicious attachment quarantined',
    preview: 'One inbound image was isolated before mailbox delivery.',
    time: 'Yesterday',
    verdict: 'QUARANTINED',
    body: 'A suspicious image attachment was blocked and moved to quarantine. The user-facing mail client can surface this status once the backend endpoint is connected.',
  },
]

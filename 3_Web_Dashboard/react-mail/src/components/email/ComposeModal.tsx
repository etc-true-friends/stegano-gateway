import * as React from 'react';
import Box from '@mui/joy/Box';
import Button from '@mui/joy/Button';
import Chip from '@mui/joy/Chip';
import Divider from '@mui/joy/Divider';
import FormControl from '@mui/joy/FormControl';
import FormHelperText from '@mui/joy/FormHelperText';
import FormLabel from '@mui/joy/FormLabel';
import IconButton from '@mui/joy/IconButton';
import Input from '@mui/joy/Input';
import Modal from '@mui/joy/Modal';
import ModalClose from '@mui/joy/ModalClose';
import ModalDialog from '@mui/joy/ModalDialog';
import Stack from '@mui/joy/Stack';
import Textarea from '@mui/joy/Textarea';
import Typography from '@mui/joy/Typography';
import Alert from '@mui/joy/Alert';
import CircularProgress from '@mui/joy/CircularProgress';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import AttachFileRoundedIcon from '@mui/icons-material/AttachFileRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import InsertDriveFileRoundedIcon from '@mui/icons-material/InsertDriveFileRounded';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import MaterialIcon from './MaterialIcon';
import { sendMail, findUserByEmail, UserInfo } from '../../api/mail';
import { getStoredAuthUser } from '../../api/auth';

type Props = {
  open: boolean;
  onClose: () => void;
};

type SendState = 'idle' | 'scanning' | 'sending' | 'done' | 'error';

export default function ComposeModal({ open, onClose }: Props) {
  const [to, setTo] = React.useState('');
  const [toTouched, setToTouched] = React.useState(false);
  const [toUser, setToUser] = React.useState<UserInfo | null>(null);
  const [toNotFound, setToNotFound] = React.useState(false);
  const [subject, setSubject] = React.useState('');
  const [body, setBody] = React.useState('');
  const [attachments, setAttachments] = React.useState<File[]>([]);
  const [sendState, setSendState] = React.useState<SendState>('idle');
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const toError = toTouched && to.length > 0 && toNotFound;
  const isValid = !!toUser && !!subject;
  const isBusy = sendState === 'scanning' || sendState === 'sending';

  const handleToBlur = async () => {
    setToTouched(true);
    if (!to.trim()) return;
    const user = await findUserByEmail(to.trim());
    if (user) {
      setToUser(user);
      setToNotFound(false);
    } else {
      setToUser(null);
      setToNotFound(true);
    }
  };

  const handleToChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTo(e.target.value);
    setToUser(null);
    setToNotFound(false);
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    setAttachments((prev) => [...prev, ...files]);
    e.target.value = '';
  };

  const handleRemoveAttachment = (idx: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== idx));
  };

  const resetForm = () => {
    setTo('');
    setToTouched(false);
    setToUser(null);
    setToNotFound(false);
    setSubject('');
    setBody('');
    setAttachments([]);
    setSendState('idle');
  };

  const handleClose = () => {
    if (isBusy) return;
    resetForm();
    onClose();
  };

  const handleSend = async () => {
    if (!isValid || isBusy) return;

    const user = getStoredAuthUser();
    if (!user) {
      setSendState('error');
      return;
    }

    try {
      setSendState(attachments.length > 0 ? 'scanning' : 'sending');

      await sendMail({
        senderId: user.id,
        recipientId: toUser!.id,
        subject,
        body,
        attachments,
      });

      setSendState('done');
      setTimeout(() => {
        resetForm();
        onClose();
      }, 1500);
    } catch {
      setSendState('error');
    }
  };

  const statusMessage: Record<SendState, { color: 'success' | 'warning' | 'neutral'; text: string; icon?: React.ReactNode } | null> = {
    idle: null,
    scanning: null,
    sending: null,
    done: {
      color: 'success',
      text: '메일이 정상적으로 전송되었습니다.',
      icon: <MaterialIcon><CheckCircleRoundedIcon /></MaterialIcon>,
    },
    error: { color: 'warning', text: '전송 중 오류가 발생했습니다. 다시 시도해주세요.' },
  };

  const alert = statusMessage[sendState];

  return (
    <Modal
      open={open}
      onClose={handleClose}
      slotProps={{ backdrop: { sx: { backdropFilter: 'none', backgroundColor: 'rgba(18, 31, 42, 0.28)' } } }}
    >
      <ModalDialog
        size="lg"
        sx={{
          width: { xs: '95vw', sm: 620 },
          maxHeight: '90vh',
          p: 0,
          overflow: 'hidden',
          borderRadius: 6,
          borderColor: '#d9e1ea',
          boxShadow: '0 22px 60px rgba(18, 31, 42, 0.22)',
        }}
      >
        <Box
          sx={{
            px: 3,
            py: 2,
            display: 'flex',
            alignItems: 'center',
            borderBottom: '1px solid',
            borderColor: '#d9e1ea',
            backgroundColor: '#f7f9fb',
          }}
        >
          <Box sx={{ flex: 1 }}>
            <Typography level="title-md">새 메일 작성</Typography>
            <Typography level="body-xs" color="neutral">
              첨부파일은 전송 전 보안검사와 CDR 무해화를 거칩니다.
            </Typography>
          </Box>
          <ModalClose sx={{ position: 'static' }} onClick={handleClose} />
        </Box>

        <Stack sx={{ px: 3, py: 2, gap: 1.5, overflow: 'auto', flex: 1 }}>
          <FormControl error={toError}>
            <FormLabel>받는 사람</FormLabel>
            <Input
              placeholder="email 입력"
              value={to}
              onChange={handleToChange}
              onBlur={handleToBlur}
              disabled={isBusy}
              sx={{ borderRadius: 6 }}
            />
            {toError && (
              <FormHelperText>존재하지 않는 사용자입니다.</FormHelperText>
            )}
          </FormControl>

          <FormControl>
            <FormLabel>제목</FormLabel>
            <Input
              placeholder="제목 입력"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              disabled={isBusy}
              sx={{ borderRadius: 6 }}
            />
          </FormControl>

          <Divider />

          <FormControl sx={{ flex: 1 }}>
            <Textarea
              placeholder="메일 내용을 입력하세요."
              minRows={8}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              sx={{ flex: 1, borderRadius: 6 }}
              disabled={isBusy}
            />
          </FormControl>

          {attachments.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
              {attachments.map((file, idx) => (
                <Chip
                  key={`${file.name}-${idx}`}
                  size="md"
                  variant="soft"
                  color="neutral"
                  startDecorator={<MaterialIcon><InsertDriveFileRoundedIcon /></MaterialIcon>}
                  endDecorator={
                    <IconButton
                      size="md"
                      variant="plain"
                      color="neutral"
                      onClick={() => handleRemoveAttachment(idx)}
                      disabled={isBusy}
                      sx={{ '--IconButton-size': '28px', pointerEvents: 'all' }}
                      aria-label={`${file.name} 첨부 제거`}
                    >
                      <MaterialIcon><CloseRoundedIcon /></MaterialIcon>
                    </IconButton>
                  }
                  sx={{ fontSize: 'sm', py: 0.5, borderRadius: 6 }}
                >
                  {file.name}
                </Chip>
              ))}
            </Box>
          )}

          {alert && (
            <Alert color={alert.color} startDecorator={alert.icon}>
              {alert.text}
            </Alert>
          )}
        </Stack>

        <Box
          sx={{
            px: 3,
            py: 2,
            display: 'flex',
            gap: 1,
            alignItems: 'center',
            borderTop: '1px solid',
            borderColor: '#d9e1ea',
            backgroundColor: '#fbfcfe',
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <IconButton
            variant="outlined"
            color="neutral"
            aria-label="첨부파일"
            onClick={handleAttachClick}
            disabled={isBusy}
          >
            <MaterialIcon><AttachFileRoundedIcon /></MaterialIcon>
          </IconButton>
          <Box sx={{ flex: 1 }} />
          {isBusy && (
            <Typography level="body-sm" color="neutral" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <CircularProgress size="sm" />
              {sendState === 'scanning' ? '첨부파일 보안검사 및 무해화 중...' : '전송 중...'}
            </Typography>
          )}
          <Button
            variant="solid"
            color="primary"
            endDecorator={<MaterialIcon><SendRoundedIcon /></MaterialIcon>}
            onClick={handleSend}
            disabled={!isValid || isBusy}
            loading={isBusy}
            sx={{ borderRadius: 6, fontWeight: 700 }}
          >
            전송
          </Button>
        </Box>
      </ModalDialog>
    </Modal>
  );
}

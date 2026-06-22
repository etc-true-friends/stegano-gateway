import * as React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import CssBaseline from '@mui/material/CssBaseline';
import FormControlLabel from '@mui/material/FormControlLabel';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import { styled } from '@mui/material/styles';
import AppTheme from '../theme/AppTheme';
import { login, saveAuthSession } from '../api/auth';

const LoginShell = styled(Stack)(({ theme }) => ({
  minHeight: '100dvh',
  alignItems: 'center',
  justifyContent: 'center',
  backgroundColor: '#ffffff',
  padding: theme.spacing(4, 2),
}));

const LoginPanel = styled(Box)(({ theme }) => ({
  width: '100%',
  maxWidth: 508,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'stretch',
  gap: theme.spacing(2.25),
}));

const DividerLine = styled(Box)({
  height: 1,
  width: '100%',
  backgroundColor: '#dddddd',
});

function TeamLogo() {
  return (
    <Box sx={{ textAlign: 'center', lineHeight: 1 }}>
      <Typography
        component="span"
        sx={{
          color: '#1f2a44',
          fontSize: { xs: 38, sm: 50 },
          fontWeight: 800,
          letterSpacing: 0,
        }}
      >
        /etc
      </Typography>
      <Typography
        component="span"
        sx={{
          color: '#2f6fd6',
          fontSize: { xs: 38, sm: 50 },
          fontWeight: 700,
          ml: 0.5,
          letterSpacing: 0,
        }}
      >
        /friends
      </Typography>
    </Box>
  );
}

export default function SignIn(props: { disableCustomTheme?: boolean }) {
  const navigate = useNavigate();
  const [emailError, setEmailError] = React.useState(false);
  const [emailErrorMessage, setEmailErrorMessage] = React.useState('');
  const [passwordError, setPasswordError] = React.useState(false);
  const [passwordErrorMessage, setPasswordErrorMessage] = React.useState('');
  const [submitError, setSubmitError] = React.useState('');
  const [loading, setLoading] = React.useState(false);

  const validateInputs = () => {
    const email = document.getElementById('email') as HTMLInputElement;
    const password = document.getElementById('password') as HTMLInputElement;
    let isValid = true;

    if (!email.value.trim()) {
      setEmailError(true);
      setEmailErrorMessage('아이디를 입력해주세요.');
      isValid = false;
    } else {
      setEmailError(false);
      setEmailErrorMessage('');
    }

    if (!password.value || password.value.length < 6) {
      setPasswordError(true);
      setPasswordErrorMessage('비밀번호는 최소 6자 이상이어야 합니다.');
      isValid = false;
    } else {
      setPasswordError(false);
      setPasswordErrorMessage('');
    }

    return isValid;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError('');

    if (!validateInputs()) {
      return;
    }

    const form = event.currentTarget;
    const email = (form.elements.namedItem('email') as HTMLInputElement).value.trim();
    const password = (form.elements.namedItem('password') as HTMLInputElement).value;

    setLoading(true);
    try {
      const result = await login(email, password);
      saveAuthSession(result.token, result.user);
      navigate('/inbox', { replace: true });
    } catch (err: unknown) {
      const message = axiosErrorMessage(err) ?? '로그인에 실패했습니다. API 서버 연결을 확인해주세요.';
      setSubmitError(message);
    } finally {
      setLoading(false);
    }
  };

  function axiosErrorMessage(err: unknown): string | null {
    if (typeof err !== 'object' || err === null || !('response' in err)) return null;
    const response = (err as { response?: { data?: { detail?: string } } }).response;
    return response?.data?.detail ?? null;
  }

  return (
    <AppTheme {...props}>
      <CssBaseline enableColorScheme />
      <LoginShell>
        <LoginPanel>
          <TeamLogo />
          <DividerLine sx={{ mt: 3, mb: 2 }} />

          <Typography
            sx={{
              textAlign: 'center',
              color: '#333',
              fontSize: 18,
              fontWeight: 400,
              mb: 4,
            }}
          >
            <Box component="span" sx={{ fontWeight: 800 }}>
              /etc/friends
            </Box>{' '}
            웹메일 시스템입니다.
          </Typography>

          <Box
            component="form"
            onSubmit={handleSubmit}
            noValidate
            sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}
          >
            <TextField
              error={emailError}
              helperText={emailErrorMessage}
              id="email"
              type="email"
              name="email"
              placeholder="아이디"
              autoComplete="email"
              autoFocus
              required
              fullWidth
              variant="outlined"
              color={emailError ? 'error' : 'primary'}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 0,
                  height: 49,
                  backgroundColor: '#fff',
                },
              }}
            />

            <TextField
              error={passwordError}
              helperText={passwordErrorMessage}
              name="password"
              placeholder="비밀번호"
              type="password"
              id="password"
              autoComplete="current-password"
              required
              fullWidth
              variant="outlined"
              color={passwordError ? 'error' : 'primary'}
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 0,
                  height: 49,
                  backgroundColor: '#fff',
                },
              }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={loading}
              onClick={validateInputs}
              sx={{
                mt: 1,
                height: 52,
                borderRadius: 0,
                backgroundColor: '#4d7de3',
                fontWeight: 700,
                boxShadow: 'none',
                '&:hover': {
                  backgroundColor: '#3f6fd2',
                  boxShadow: 'none',
                },
              }}
            >
              {loading ? '로그인 중...' : '로그인'}
            </Button>

            <FormControlLabel
              control={<Checkbox value="remember" color="primary" />}
              label="로그인 상태 유지"
              sx={{ mt: 1.25, color: '#404a56' }}
            />

            {submitError && (
              <Typography color="error" variant="body2" sx={{ textAlign: 'center' }}>
                {submitError}
              </Typography>
            )}
          </Box>

          <DividerLine sx={{ mt: 4 }} />
          <Typography sx={{ textAlign: 'center', color: '#777', fontSize: 11, mt: 1 }}>
            Copyright 2026. /etc/friends. All rights reserved.
          </Typography>
        </LoginPanel>
      </LoginShell>
    </AppTheme>
  );
}

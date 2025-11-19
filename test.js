import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 1,
  duration: '10s',
};

export default function () {
  const res = http.get('http://127.0.0.1:8000/');
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  console.log(`Status: ${res.status}, Body: ${res.body}`);
}



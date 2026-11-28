export function sessionJwt(sub, jti, iat, ver = 0, iss = 'smartprop') {
  const encode = value => Buffer.from(JSON.stringify(value)).toString('base64url');
  return encode({ alg: 'fixture' }) + '.' + encode({ iss, sub: String(sub), jti, ver, iat }) + '.fixture';
}

export interface BatchUserInput {
  uid?: string;
  userName: string;
  nickName?: string;
  email?: string;
  phone?: string;
  password: string;
}
export interface BatchResult {
  row: number;
  id: number | null;
  userName: string | null;
  success: boolean;
  code: string;
  message: string;
}

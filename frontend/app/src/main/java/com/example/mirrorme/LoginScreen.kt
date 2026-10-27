package com.example.mirrorme

import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mirrorme.ui.theme.MirrorMeTheme
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoginScreen(
    onLoginClick: (String, String) -> Unit = { _, _ -> },
    onSignUpClick: () -> Unit = {}
) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .padding(horizontal = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(80.dp))

        // 로고 (Logo)
        Image(
            painter = painterResource(id = R.drawable.mirrorme_logo_header),
            contentDescription = "MirrorMe Logo",
            modifier = Modifier.height(50.dp),
            contentScale = ContentScale.Fit
        )

        Spacer(modifier = Modifier.height(40.dp))

        // 로그인 제목
        Text(
            text = "로그인",
            fontFamily = MM_Font,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            color = Color.Black
        )

        Spacer(modifier = Modifier.height(24.dp))

        // 이메일 입력
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            placeholder = { 
                Text(
                    text = "email@domain.com", 
                    color = Color.Gray.copy(alpha = 0.6f),
                    fontFamily = MM_Font
                ) 
            },
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(8.dp),
            colors = OutlinedTextFieldDefaults.colors(
                unfocusedBorderColor = Color.LightGray.copy(alpha = 0.5f),
                focusedBorderColor = Color.Black,
                focusedContainerColor = Color.Transparent,
                unfocusedContainerColor = Color.Transparent
            ),
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email)
        )

        Spacer(modifier = Modifier.height(12.dp))

        // 비밀번호 입력
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            placeholder = { 
                Text(
                    text = "비밀번호", 
                    color = Color.Gray.copy(alpha = 0.6f),
                    fontFamily = MM_Font
                ) 
            },
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(8.dp),
            visualTransformation = PasswordVisualTransformation(),
            colors = OutlinedTextFieldDefaults.colors(
                unfocusedBorderColor = Color.LightGray.copy(alpha = 0.5f),
                focusedBorderColor = Color.Black,
                focusedContainerColor = Color.Transparent,
                unfocusedContainerColor = Color.Transparent
            ),
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password)
        )

        Spacer(modifier = Modifier.height(24.dp))

        // 계속 버튼
        Button(
            onClick = {
                if (email.isBlank() || password.isBlank()) {
                    Toast.makeText(context, "이메일과 비밀번호를 입력해주세요.", Toast.LENGTH_SHORT).show()
                    return@Button
                }
                isLoading = true
                val loginData = mapOf(
                    "email" to email,
                    "password" to password
                )
                RetrofitClient.service.login(loginData).enqueue(object : Callback<Map<String, Any>> {
                    override fun onResponse(call: Call<Map<String, Any>>, response: Response<Map<String, Any>>) {
                        isLoading = false
                        if (response.isSuccessful && response.body()?.get("success") == true) {
                            val userId = response.body()?.get("user_id") as? String ?: "guest"
                            val nickname = response.body()?.get("nickname") as? String ?: ""
                            Toast.makeText(context, "${nickname}님 환영합니다!", Toast.LENGTH_SHORT).show()
                            onLoginClick(userId, nickname)
                        } else {
                            val message = response.body()?.get("message") as? String ?: "로그인 실패"
                            Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
                        }
                    }

                    override fun onFailure(call: Call<Map<String, Any>>, t: Throwable) {
                        isLoading = false
                        Toast.makeText(context, "네트워크 오류: ${t.localizedMessage}", Toast.LENGTH_SHORT).show()
                    }
                })
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            enabled = !isLoading,
            colors = ButtonDefaults.buttonColors(containerColor = Color.Black),
            shape = RoundedCornerShape(8.dp)
        ) {
            if (isLoading) {
                CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
            } else {
                Text(
                    text = "계속",
                    fontFamily = MM_Font,
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 회원가입 유도
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "계정이 없으신가요?",
                fontFamily = MM_Font,
                color = Color.Gray,
                fontSize = 14.sp
            )
            TextButton(onClick = onSignUpClick) {
                Text(
                    text = "회원가입",
                    fontFamily = MM_Font,
                    color = Color.Black,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
            }
        }

        Spacer(modifier = Modifier.weight(1f))

        // 푸터 텍스트
        Text(
            text = "계속을 클릭하면 당사의 서비스 이용 약관 및 개인정보 처리방침에 동의하는 것으로 간주됩니다.",
            fontFamily = MM_Font,
            color = Color.Gray,
            fontSize = 12.sp,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(bottom = 32.dp),
            lineHeight = 18.sp
        )
    }
}

@Preview(showBackground = true)
@Composable
fun LoginScreenPreview() {
    MirrorMeTheme {
        LoginScreen()
    }
}

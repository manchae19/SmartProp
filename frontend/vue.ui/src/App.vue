<script setup>
// Không cần xử lý logic thủ công ở đây vì đã có Vue Router lo việc điều hướng
</script>

<template>
  <div id="app">
    <!-- Component này sẽ tự động hiển thị LoginView hoặc DashboardView tùy theo đường dẫn URL -->
    <router-view />
  </div>
</template>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
</style>
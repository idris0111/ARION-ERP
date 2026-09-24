from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = [
        ('SUPER_ADMIN', 'Super Admin'),
        ('ADMIN', 'Admin'),
        ('DIRECTOR', 'Director'),
        ('CHIEF_ACCOUNTANT', 'Chief Accountant'),
        ('ACCOUNTANT', 'Accountant'),
        ('MANAGER', 'Manager'),
        ('SALES_MANAGER', 'Sales Manager'),
        ('PURCHASE_MANAGER', 'Purchase Manager'),
        ('WAREHOUSE_MANAGER', 'Warehouse Manager'),
        ('STOREKEEPER', 'Storekeeper'),
        ('CASHIER', 'Cashier'),
        ('HR', 'HR'),
        ('AUDITOR', 'Auditor'),
        ('ANALYST', 'Analyst'),
        ('OPERATOR', 'Operator'),
        ('EMPLOYEE', 'Employee'),
        ('VIEWER', 'Viewer'),
    ]

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='EMPLOYEE'
    )

    phone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )

    avatar = models.ImageField(
        upload_to='',
        null=True,
        blank=True
    )

    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    middle_name = models.CharField(
        max_length=150,
        blank=True
    )

    address = models.CharField(
        max_length=255,
        blank=True
    )

    birth_date = models.DateField(
        null=True,
        blank=True
    )

    passport = models.CharField(
        max_length=100,
        blank=True
    )

    position = models.CharField(
        max_length=150,
        blank=True
    )

    hire_date = models.DateField(
        null=True,
        blank=True
    )

    salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    is_employee = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username
from django.db.models import Model
from rest_framework import serializers

from .models import (Account,CRMActivity,CRMTask,Deal,DealStage,DebtPayment,
    JournalEntry,JournalEntryLine,Lead,StockReservation)
from .tenancy import ensure_organization_access,get_object_organization_id


class OrganizationModelSerializer(serializers.ModelSerializer):
    def run_validation(self,data=serializers.empty):
        validated = super().run_validation(data)
        request = self.context.get('request')
        if request:
            objects = [value for value in validated.values() if isinstance(value,Model)]
            if self.instance is not None:
                objects.append(self.instance)
            ensure_organization_access(request.user,*objects)
            organization_ids = {get_object_organization_id(obj) for obj in objects if get_object_organization_id(obj) is not None}
            if len(organization_ids) > 1:
                raise serializers.ValidationError('Связанные объекты относятся к разным организациям')
        return validated


class StockReservationSerializer(OrganizationModelSerializer):
    class Meta:
        model = StockReservation
        fields = '__all__'
        read_only_fields = ['status','created_by','released_at']

    def validate_quantity(self,value):
        if value <= 0:
            raise serializers.ValidationError('Количество должно быть больше 0')
        return value

    def validate(self,data):
        warehouse = data.get('warehouse')
        product = data.get('product')
        organization = data.get('organization')
        if warehouse and organization and warehouse.organization_id != organization.pk:
            raise serializers.ValidationError('Склад относится к другой организации')
        if product and organization and product.organization_id != organization.pk:
            raise serializers.ValidationError('Товар относится к другой организации')
        return data


class DebtPaymentSerializer(OrganizationModelSerializer):
    class Meta:
        model = DebtPayment
        fields = '__all__'
        read_only_fields = ['created_by','created_at','cash_transaction']


class AccountSerializer(OrganizationModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'


class JournalEntryLineSerializer(OrganizationModelSerializer):
    class Meta:
        model = JournalEntryLine
        fields = '__all__'

    def validate(self,data):
        debit = data.get('debit',0)
        credit = data.get('credit',0)
        if debit < 0 or credit < 0 or bool(debit) == bool(credit):
            raise serializers.ValidationError('Укажите положительный дебет или кредит')
        entry = data.get('journal_entry') or getattr(self.instance,'journal_entry',None)
        if entry and entry.status != 'DRAFT':
            raise serializers.ValidationError('Строки можно менять только в черновике')
        return data


class JournalEntrySerializer(OrganizationModelSerializer):
    lines = JournalEntryLineSerializer(many=True,read_only=True)
    debit_total = serializers.SerializerMethodField()
    credit_total = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = '__all__'
        read_only_fields = ['status','created_by']

    def get_debit_total(self,obj):
        return sum((line.debit for line in obj.lines.all()),0)

    def get_credit_total(self,obj):
        return sum((line.credit for line in obj.lines.all()),0)


class DealStageSerializer(OrganizationModelSerializer):
    class Meta:
        model = DealStage
        fields = '__all__'


class LeadSerializer(OrganizationModelSerializer):
    class Meta:
        model = Lead
        fields = '__all__'
        read_only_fields = ['customer']

    def validate_probability(self,value):
        if value > 100:
            raise serializers.ValidationError('Вероятность должна быть от 0 до 100')
        return value


class DealSerializer(OrganizationModelSerializer):
    class Meta:
        model = Deal
        fields = '__all__'

    def validate_probability(self,value):
        if value > 100:
            raise serializers.ValidationError('Вероятность должна быть от 0 до 100')
        return value


class CRMTaskSerializer(OrganizationModelSerializer):
    class Meta:
        model = CRMTask
        fields = '__all__'

    def validate(self,data):
        lead = data.get('lead') or getattr(self.instance,'lead',None)
        deal = data.get('deal') or getattr(self.instance,'deal',None)
        if not lead and not deal:
            raise serializers.ValidationError('Укажите lead или deal')
        return data


class CRMActivitySerializer(OrganizationModelSerializer):
    class Meta:
        model = CRMActivity
        fields = '__all__'
        read_only_fields = ['created_by']

    def validate(self,data):
        if not any(data.get(field) or getattr(self.instance,field,None) for field in ('customer','lead','deal')):
            raise serializers.ValidationError('Укажите customer, lead или deal')
        return data
